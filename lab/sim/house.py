"""Grey-box thermal model of the house: underfloor loop + slab + room + envelope + thermometer.

Identified from this house's measured data (see docs/research/lab/HOUSE_MODEL.md and
lab/sim/house_ident.py). It does not reuse the Home Assistant integration's code or model.

Structure (central fit; alternatives are documented in the report)
-------------------------------------------------------------------
States (degC):
- `w1..wN`: loop water in N segments in series (water + pipe mass). The water enters segment 1
  at the supply temperature (or at the return + heat / (cp flow) when heat is the input) and
  leaves segment N as the return to the heat pump. Each segment exchanges heat with the slab.
- `s`: slab/screed around the pipes.
- `a`: room air plus furniture and light internal mass (what the living-room sensor sees).
- `e`: building envelope (walls, ceiling: the slow store between the room and outdoors).
- `m`: the thermometer (first-order lag behind the air).
- `g`: 'glow' of the thermometer in direct sun (a fast additive reading, not real air warming).

Heat flows (kW): loop -> slab (u_ws, split evenly over the segments); slab -> air (k_sa);
air -> envelope (k_ae); envelope -> outdoors (h_eo); air -> outdoors directly (h_ao: windows,
infiltration, ventilation after heat recovery); slab -> ground (h_g, to a fixed ground
temperature). Solar gain = sum of effective apertures (m2) x facade irradiance (W/m2), a
fraction `f_sol_slab` lands on the slab, the rest on the air node. Internal gain = constant +
daily profile (two harmonics of local hour) + any extra/disturbance heat given at step time.

Conventions: temperatures degC; heat kW; capacities kWh/K; conductances kW/K; flow L/min; the
step length is given in minutes (default 1). The return temperature is on the scale of the unit's
inlet sensor, like `t_supply` in lab/sim/unit.py, so the two models connect directly:

    r = unit.step(sp, delta, t_return=house.t_return, t_amb=...)
    h = house.step(t_out=..., q_loop=r.q_loop, ...)            # heat as input (energy-exact)
    # or: house.step(t_out=..., t_supply=r.t_supply, flow_lpm=r.loop_flow_lpm, ...)

Run `python -m lab.sim.house` for the physics self-check.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.linalg import expm

CP_WATER = 4.186  # kJ/(kg K)
RHO_CP_AIR_KWH_M3K = 1.2 * 1.006 / 3600.0  # kWh/(m3 K)

# input vector of the linear system (same order everywhere)
U_NAMES = ("q", "t_out", "poa_s", "poa_e", "poa_w", "ghi", "one", "c1", "s1", "c2", "s2",
           "i_glow", "q_air", "q_slab")


@dataclass
class HouseParams:
    """Parameters of the central fit. `ranges` holds the uncertainty (see the report)."""

    # loop
    n_seg: int = 3  # 1, 3 and 6 segments fit equally well; 3 is the central choice
    c_w: float = 0.264  # kWh/K, water + pipes in the floor loop (~230 L water-equivalent)
    u_ws: float = 2.53  # kW/K, water -> slab
    flow_lpm: float = 29.0  # nominal loop flow (unit stage)
    # slab
    c_s: float = 4.40  # kWh/K
    k_sa: float = 0.427  # kW/K, slab -> room air
    h_g: float = 0.092  # kW/K, slab -> ground (also absorbs a weather-independent loss)
    t_ground: float = 10.0  # degC
    # room air + furniture
    c_a: float = 4.27  # kWh/K (air + furniture + light internal mass)
    h_ao: float = 0.045  # kW/K, direct to outdoors (windows, infiltration, ventilation)
    # envelope
    c_e: float = 74.3  # kWh/K (0 removes the node): walls, ceiling, internal heavy mass
    k_ae: float = 1.348  # kW/K
    h_eo: float = 0.0696  # kW/K
    # ventilation (documented part of h_ao; heat recovery)
    vent_m3h: float = 40.0
    vent_eta: float = 0.85
    # solar (effective apertures, m2) and split
    a_s: float = 2.69
    a_e: float = 6.41
    a_w: float = 3.74
    a_h: float = 0.0  # tested: no gain over the facades
    f_sol_slab: float = 0.022  # fit: almost all sun acts on the air/furniture node
    # internal gains (kW): constant + daily profile in local hours
    q_int: float = 0.313
    q_c1: float = -0.201
    q_s1: float = -0.243
    q_c2: float = 0.153
    q_s2: float = -0.117
    # thermometer
    tau_m_h: float = 0.0  # sensor lag (h); 0 removes the node (the joint fit drives it to ~0.4 min)
    g_glow: float = 0.00082  # K per (W/m2) of GHI: 0.4 K at 500 W/m2 (sun on the thermometer)
    tau_g_h: float = 0.05
    glow_src: str = "ghi"
    sensor_res: float = 0.1
    ranges: dict = field(default_factory=dict)

    @property
    def k_flow(self) -> float:
        return CP_WATER * self.flow_lpm / 60.0

    @property
    def h_vent(self) -> float:
        return RHO_CP_AIR_KWH_M3K * self.vent_m3h * (1.0 - self.vent_eta)

    @property
    def h_total(self) -> float:
        """Heat-loss coefficient room -> outdoors plus the ground path seen from the room, kW/K.
        The ground path ends at t_ground, not outdoors; use steady_heat() for loads."""
        env = 0.0
        if self.c_e > 0:
            env = 1.0 / (1.0 / self.k_ae + 1.0 / self.h_eo)
        return self.h_ao + env + self.h_g_equiv

    @property
    def h_g_equiv(self) -> float:
        # ground loss seen from the room (in series with the slab-air link)
        if self.h_g <= 0:
            return 0.0
        return 1.0 / (1.0 / self.h_g + 1.0 / self.k_sa)

    def internal_kw(self, hour_local: float) -> float:
        w = 2.0 * math.pi * hour_local / 24.0
        return (self.q_int + self.q_c1 * math.cos(w) + self.q_s1 * math.sin(w)
                + self.q_c2 * math.cos(2 * w) + self.q_s2 * math.sin(2 * w))


# ------------------------------------------------------------------------------------------
# linear system
# ------------------------------------------------------------------------------------------

def state_names(p: HouseParams):
    names = [f"w{i + 1}" for i in range(p.n_seg)] + ["s", "a"]
    if p.c_e > 0:
        names.append("e")
    if p.tau_m_h > 0:
        names.append("m")
    if p.g_glow != 0:
        names.append("g")
    return names


def matrices(p: HouseParams, mode: str = "heat", flow_lpm: float | None = None):
    """Continuous-time dx/dt = A x + B u (per hour), y = C x (room sensor, return).

    mode 'heat': u[0] is heat into the loop (kW) at the nominal flow (water enters at
    return + q / (cp flow)). mode 'supply': u[0] is the supply temperature at `flow_lpm`."""
    names = state_names(p)
    ix = {k: i for i, k in enumerate(names)}
    n, m = len(names), len(U_NAMES)
    iu = {k: i for i, k in enumerate(U_NAMES)}
    A = np.zeros((n, n))
    B = np.zeros((n, m))
    N = p.n_seg
    flow = p.flow_lpm if flow_lpm is None else flow_lpm
    k = CP_WATER * flow / 60.0
    cw = p.c_w / N
    uw = p.u_ws / N
    s, a = ix["s"], ix["a"]
    for i in range(N):
        wi = ix[f"w{i + 1}"]
        A[wi, wi] -= (k + uw) / cw
        A[wi, s] += uw / cw
        A[s, wi] += uw / p.c_s
        A[s, s] -= uw / p.c_s
        if i > 0:
            A[wi, ix[f"w{i}"]] += k / cw
    w1, wN = ix["w1"], ix[f"w{N}"]
    if mode == "heat":
        A[w1, wN] += k / cw
        B[w1, iu["q"]] = 1.0 / cw
    else:
        B[w1, iu["q"]] = k / cw
    # slab <-> air, ground
    A[s, s] -= (p.k_sa + p.h_g) / p.c_s
    A[s, a] += p.k_sa / p.c_s
    B[s, iu["one"]] += p.h_g * p.t_ground / p.c_s
    A[a, a] -= (p.k_sa + p.h_ao) / p.c_a
    A[a, s] += p.k_sa / p.c_a
    B[a, iu["t_out"]] += p.h_ao / p.c_a
    if p.c_e > 0:
        e = ix["e"]
        A[a, a] -= p.k_ae / p.c_a
        A[a, e] += p.k_ae / p.c_a
        A[e, a] += p.k_ae / p.c_e
        A[e, e] -= (p.k_ae + p.h_eo) / p.c_e
        B[e, iu["t_out"]] += p.h_eo / p.c_e
    # solar (W/m2 x m2 -> kW)
    for name, ap in (("poa_s", p.a_s), ("poa_e", p.a_e), ("poa_w", p.a_w), ("ghi", p.a_h)):
        B[s, iu[name]] += p.f_sol_slab * ap / 1000.0 / p.c_s
        B[a, iu[name]] += (1.0 - p.f_sol_slab) * ap / 1000.0 / p.c_a
    # internal gains
    B[a, iu["one"]] += p.q_int / p.c_a
    for name, v in (("c1", p.q_c1), ("s1", p.q_s1), ("c2", p.q_c2), ("s2", p.q_s2)):
        B[a, iu[name]] += v / p.c_a
    B[a, iu["q_air"]] += 1.0 / p.c_a
    B[s, iu["q_slab"]] += 1.0 / p.c_s
    # thermometer
    C = np.zeros((2, n))
    if p.tau_m_h > 0:
        mi = ix["m"]
        A[mi, mi] = -1.0 / p.tau_m_h
        A[mi, a] = 1.0 / p.tau_m_h
        C[0, mi] = 1.0
    else:
        C[0, a] = 1.0
    if p.g_glow != 0:
        gi = ix["g"]
        A[gi, gi] = -1.0 / p.tau_g_h
        B[gi, iu["i_glow"]] = p.g_glow / p.tau_g_h
        C[0, gi] = 1.0
    C[1, wN] = 1.0
    return A, B, C, names


def discretize(A, B, dt_h):
    n, m = B.shape
    M = np.zeros((n + m, n + m))
    M[:n, :n] = A
    M[:n, n:] = B
    E = expm(M * dt_h)
    return E[:n, :n], E[:n, n:]


# ------------------------------------------------------------------------------------------
# solar helper (same transposition as the lab weather columns)
# ------------------------------------------------------------------------------------------

def facade_irradiance(ghi, dni, dhi, sun_elev_deg, sun_az_deg, facade_az_deg, albedo=0.2):
    """Irradiance on a vertical facade (W/m2): beam + isotropic sky + ground reflection."""
    el = math.radians(sun_elev_deg)
    if sun_elev_deg <= 0:
        beam = 0.0
    else:
        cos_inc = math.cos(el) * math.cos(math.radians(sun_az_deg - facade_az_deg))
        beam = max(dni * cos_inc, 0.0)
    return beam + 0.5 * dhi + 0.5 * albedo * ghi


# ------------------------------------------------------------------------------------------
# dynamic model
# ------------------------------------------------------------------------------------------

@dataclass
class HouseStep:
    t_return: float  # loop water back to the heat pump (inlet-sensor scale)
    t_air: float  # room air node
    t_sensor_true: float  # what the thermometer feels (lag + glow), unquantized
    t_sensor: float  # reported value (quantized, report-on-change)
    t_slab: float
    t_envelope: float
    q_loop: float  # heat into the loop this step (kW)
    q_floor: float  # slab -> air (kW)
    q_loss: float  # air/envelope/ground -> outside (kW, end of step)
    q_solar: float  # total solar gain (kW)
    q_internal: float  # modelled internal gains (kW, excl. disturbance)


class House:
    """Stateful model; call step() once per time step (default 1 minute)."""

    def __init__(self, params: HouseParams | None = None, t_init: float = 22.0,
                 t_out_init: float | None = None, t_slab_init: float | None = None):
        self.p = params or HouseParams()
        self._cache = {}
        A, B, C, names = matrices(self.p, "heat")
        self.names = names
        self.ix = {k: i for i, k in enumerate(names)}
        self.C = C
        self.x = np.zeros(len(names))
        self.reset(t_init, t_out_init, t_slab_init)
        self._reported = None

    # -- state helpers ------------------------------------------------------------------
    def reset(self, t_air=22.0, t_out=None, t_slab=None):
        """Quasi-steady initial state: air at t_air, slab at t_slab (default from a steady
        balance at t_out with no sun), envelope between air and outdoors, loop at the slab."""
        p, ix = self.p, self.ix
        t_out = 5.0 if t_out is None else t_out
        loss = p.h_ao * (t_air - t_out)
        te = t_air
        if p.c_e > 0:
            te = (p.k_ae * t_air + p.h_eo * t_out) / (p.k_ae + p.h_eo)
            loss += p.k_ae * (t_air - te)
        if t_slab is None:
            t_slab = t_air + max(loss - p.q_int, 0.0) / p.k_sa
        for i in range(p.n_seg):
            self.x[ix[f"w{i + 1}"]] = t_slab
        self.x[ix["s"]] = t_slab
        self.x[ix["a"]] = t_air
        if "e" in ix:
            self.x[ix["e"]] = te
        if "m" in ix:
            self.x[ix["m"]] = t_air
        if "g" in ix:
            self.x[ix["g"]] = 0.0
        self._reported = None

    def set_state(self, **kw):
        for k, v in kw.items():
            self.x[self.ix[k]] = v

    @property
    def t_return(self) -> float:
        return float(self.x[self.ix[f"w{self.p.n_seg}"]])

    @property
    def t_air(self) -> float:
        return float(self.x[self.ix["a"]])

    @property
    def t_slab(self) -> float:
        return float(self.x[self.ix["s"]])

    def _disc(self, mode, flow, dt_min):
        key = (mode, round(flow, 3), dt_min)
        if key not in self._cache:
            A, B, _, _ = matrices(self.p, mode, flow)
            self._cache[key] = discretize(A, B, dt_min / 60.0)
        return self._cache[key]

    def _quantize(self, v):
        res = self.p.sensor_res
        if self._reported is None or abs(v - self._reported) >= 0.75 * res:
            self._reported = round(v / res) * res
        return self._reported

    # -- main step --------------------------------------------------------------------
    def step(self, t_out: float, q_loop: float | None = None, t_supply: float | None = None,
             flow_lpm: float | None = None, poa_s: float = 0.0, poa_e: float = 0.0,
             poa_w: float = 0.0, ghi: float = 0.0, hour_local: float | None = None,
             q_air: float = 0.0, q_slab: float = 0.0, i_glow: float | None = None,
             dt_min: float = 1.0) -> HouseStep:
        """Advance one step. Give either `q_loop` (kW into the loop at the nominal flow) or
        `t_supply` with `flow_lpm` (0 = loop not flowing, e.g. valve on the tank side).
        `q_air` / `q_slab` are extra heat (kW): disturbances, people, cooking (negative for
        airing). `hour_local` switches on the fitted daily internal-gain profile (otherwise
        only the constant part). `i_glow` defaults to the facade named by params.glow_src."""
        p = self.p
        x0 = self.x.copy()
        ret0 = self.t_return
        if t_supply is not None:
            flow = p.flow_lpm if flow_lpm is None else flow_lpm
            Ad, Bd = self._disc("supply", flow, dt_min)
            u0 = t_supply
        else:
            flow = p.flow_lpm
            Ad, Bd = self._disc("heat", flow, dt_min)
            u0 = 0.0 if q_loop is None else q_loop
        if hour_local is None:
            c1 = s1 = c2 = s2 = 0.0
        else:
            w = 2.0 * math.pi * hour_local / 24.0
            c1, s1, c2, s2 = math.cos(w), math.sin(w), math.cos(2 * w), math.sin(2 * w)
        if i_glow is None:
            i_glow = {"poa_s": poa_s, "poa_e": poa_e, "poa_w": poa_w, "ghi": ghi}.get(p.glow_src, 0.0)
        u = np.array([u0, t_out, poa_s, poa_e, poa_w, ghi, 1.0, c1, s1, c2, s2, i_glow, q_air, q_slab])
        self.x = Ad @ self.x + Bd @ u
        ret1 = self.t_return
        if t_supply is not None:
            q_in = CP_WATER * flow / 60.0 * (t_supply - 0.5 * (ret0 + ret1))
        else:
            q_in = u0
        ix = self.ix
        s, a = self.x[ix["s"]], self.x[ix["a"]]
        y = float(self.C[0] @ self.x)
        loss = p.h_ao * (a - t_out) + p.h_g * (s - p.t_ground)
        te = a
        if "e" in ix:
            te = self.x[ix["e"]]
            loss += p.h_eo * (te - t_out)
        q_sol = (p.a_s * poa_s + p.a_e * poa_e + p.a_w * poa_w + p.a_h * ghi) / 1000.0
        q_int = p.q_int if hour_local is None else p.internal_kw(hour_local)
        del x0
        return HouseStep(ret1, float(a), y, self._quantize(y), float(s), float(te), float(q_in),
                         float(p.k_sa * (s - a)), float(loss), q_sol, q_int)

    # -- steady state -----------------------------------------------------------------
    def steady_heat(self, t_air: float, t_out: float, q_gain: float = 0.0) -> float:
        """Steady loop heat (kW) that holds the air at t_air with t_out, the constant internal
        gain and extra gains q_gain on the air node (no sun). Includes the ground path."""
        return steady_heat(self.p, t_air, t_out, q_gain)


def steady_state(p: HouseParams, q_loop: float, t_out: float, q_air: float = 0.0):
    """Steady state vector (and names) for constant heat, outdoor temperature and gains."""
    A, B, _, names = matrices(p, "heat")
    u = np.zeros(len(U_NAMES))
    u[0], u[1], u[6], u[12] = q_loop, t_out, 1.0, q_air
    return np.linalg.solve(A, -B @ u), names


def steady_heat(p: HouseParams, t_air: float, t_out: float, q_gain: float = 0.0) -> float:
    x0, names = steady_state(p, 0.0, t_out, q_gain)
    x1, _ = steady_state(p, 1.0, t_out, q_gain)
    ia = names.index("a")
    return max((t_air - x0[ia]) / (x1[ia] - x0[ia]), 0.0)


# ------------------------------------------------------------------------------------------
# fitted parameter sets and variants (filled from lab/sim/house_ident.py)
# ------------------------------------------------------------------------------------------

_V = dict(
    heavy_slab=dict(c_w=0.2706, u_ws=2.352, c_s=5.7184, k_sa=0.4785, h_g=0.0934, c_a=4.1358, h_ao=0.0448,
                    c_e=75.6375, k_ae=1.2939, h_eo=0.0749, a_s=2.7687, a_e=6.1588, a_w=3.7135, f_sol_slab=0.0,
                    q_int=0.431, q_c1=-0.1542, q_s1=-0.2337, q_c2=0.1475, q_s2=-0.1104, g_glow=0.0007),
    light_slab=dict(c_w=0.3256, u_ws=2.8024, c_s=3.0791, k_sa=0.4033, h_g=0.0871, c_a=4.8916, h_ao=0.046,
                    c_e=74.0201, k_ae=1.471, h_eo=0.0649, a_s=2.89, a_e=6.2077, a_w=3.8881, f_sol_slab=0.0519,
                    q_int=0.1486, q_c1=-0.3226, q_s1=-0.2509, q_c2=0.1669, q_s2=-0.1147, g_glow=0.0011),
    loss_plus20=dict(c_w=0.2284, u_ws=2.4199, c_s=4.8017, k_sa=0.5056, h_g=0.1105, c_a=4.7321, h_ao=0.054,
                     c_e=107.4722, k_ae=1.6172, h_eo=0.0835, a_s=3.0252, a_e=6.8318, a_w=4.8453, f_sol_slab=0.089,
                     q_int=1.0621, q_c1=-0.2167, q_s1=-0.2497, q_c2=0.1363, q_s2=-0.1432, tau_m_h=0.161,
                     g_glow=0.0013),
    loss_minus20=dict(c_w=0.2275, u_ws=2.6827, c_s=4.4463, k_sa=0.2802, h_g=0.0737, c_a=3.6484, h_ao=0.036,
                      c_e=71.9978, k_ae=1.0782, h_eo=0.0557, a_s=1.7757, a_e=5.7926, a_w=3.4991, f_sol_slab=0.0,
                      q_int=-0.3106, q_c1=-0.0701, q_s1=-0.1354, q_c2=0.1422, q_s2=-0.0988, g_glow=0.0007),
    sun_plus30=dict(c_w=0.2658, u_ws=2.5757, c_s=4.3984, k_sa=0.5881, h_g=0.062, c_a=5.5837, h_ao=0.0584,
                    c_e=98.2822, k_ae=1.6588, h_eo=0.0664, a_s=3.4971, a_e=8.3337, a_w=4.8556, f_sol_slab=0.0,
                    q_int=-0.1512, q_c1=-0.2617, q_s1=-0.2183, q_c2=0.2147, q_s2=-0.1583, g_glow=0.0006),
    sun_minus30=dict(c_w=0.2173, u_ws=2.4709, c_s=4.47, k_sa=0.2138, h_g=0.1402, c_a=2.5564, h_ao=0.0264,
                     c_e=51.3886, k_ae=0.8733, h_eo=0.0603, a_s=1.883, a_e=4.4874, a_w=2.6146, f_sol_slab=0.1641,
                     q_int=0.6809, q_c1=-0.093, q_s1=-0.1582, q_c2=0.0863, q_s2=-0.0548, g_glow=0.0008),
    # fitted on the minute data only (no cold-season energy constraint): smaller ground term,
    # higher outdoor coupling; overstates deep-cold heat demand by ~20-35 % (see report)
    minute_only=dict(c_w=0.3484, u_ws=2.4064, c_s=4.5294, k_sa=0.5561, h_g=0.0417, c_a=3.5071, h_ao=0.068,
                     c_e=35.5969, k_ae=1.3521, h_eo=0.109, a_s=2.7128, a_e=7.7841, a_w=2.1731, f_sol_slab=0.0,
                     q_int=0.3619, q_c1=-0.0637, q_s1=-0.3194, q_c2=-0.077, q_s2=0.0417, tau_m_h=0.316,
                     g_glow=0.0007),
)

_RANGES = {
    "c_s (kWh/K)": (3.1, 5.7),
    "h_total (kW/K)": (0.15, 0.22),
    "solar apertures x": (0.7, 1.3),
    "k_sa (kW/K)": (0.28, 0.59),
    "u_ws (kW/K)": (2.35, 2.80),
    "flow_lpm (unit stage)": (25.0, 33.0),
}


def central() -> HouseParams:
    """Joint fit: minute multi-step errors (Feb-Nov 2026) + hourly cold-season (Jan-Feb 2026)."""
    return HouseParams(ranges=dict(_RANGES))


def _variant(name):
    def f() -> HouseParams:
        return replace(central(), **_V[name])
    f.__name__ = name
    f.__doc__ = f"Profile refit with one aspect fixed: {name} (see HOUSE_MODEL.md)."
    return f


def flow_scaled(p: HouseParams, flow_lpm: float) -> HouseParams:
    """Pair with the unit model's low_flow/high_flow variants. Every measured heat number scales
    with the assumed loop flow, so a house fitted at 29 L/min is reproduced exactly at another
    flow by scaling all capacities, conductances, apertures and gains by flow / 29."""
    f = flow_lpm / p.flow_lpm
    kw = {k: getattr(p, k) * f for k in ("c_w", "u_ws", "c_s", "k_sa", "h_g", "c_a", "h_ao", "c_e", "k_ae",
                                         "h_eo", "a_s", "a_e", "a_w", "a_h", "q_int", "q_c1", "q_s1", "q_c2", "q_s2")}
    return replace(p, flow_lpm=flow_lpm, **kw)


VARIANTS = {"central": central, **{k: _variant(k) for k in _V}}


def _self_check():
    import time

    p = central()
    print(f"central: H_total {p.h_total:.3f} kW/K (outdoors {p.h_total - p.h_g_equiv:.3f}, "
          f"ground {p.h_g_equiv:.3f}), C slab {p.c_s} kWh/K")
    # 1) steady state: solve A x + B u = 0 and check the heat balance through House.step
    for t_out, q in ((-15.0, 6.0), (0.0, 3.0), (10.0, 1.0)):
        A, B, C, names = matrices(p, "heat")
        u = np.zeros(len(U_NAMES))
        u[0], u[1], u[6] = q, t_out, 1.0
        x = np.linalg.solve(A, -B @ u)
        h = House(p)
        h.x = x.copy()
        r = None
        for _ in range(600):
            r = h.step(t_out=t_out, q_loop=q)
        drift = float(np.max(np.abs(h.x - x)))
        bal = q + p.q_int - r.q_loss
        assert drift < 1e-6 and abs(bal) < 1e-6, (drift, bal)
        ta = x[names.index("a")]
        print(f"  steady t_out {t_out:+.0f}, heat {q:.1f} kW: air {ta:.2f}, slab {x[names.index('s')]:.2f}, "
              f"return {x[p.n_seg - 1]:.2f} degC; balance error {bal:.1e} kW")
    # 2) no heat, no gains: everything decays monotonically towards outdoors (ground at outdoors too)
    p0 = replace(p, q_int=0.0, q_c1=0.0, q_s1=0.0, q_c2=0.0, q_s2=0.0, t_ground=0.0)
    h = House(p0, t_init=22.0, t_out_init=0.0)
    prev = h.t_air
    for k in range(60 * 24 * 60):
        r = h.step(t_out=0.0)
        if k % 60 == 0:
            assert r.t_air <= prev + 1e-9
            prev = r.t_air
    assert 0.0 < h.t_air < 3.0 and float(np.max(np.abs(h.x))) < 3.0
    lam = np.linalg.eigvals(matrices(p, "heat")[0]).real
    assert np.all(lam < 0)
    tc = sorted(-1.0 / lam)
    print(f"  decay without gains: air {h.t_air:.2f} degC after 60 days; time constants (h): "
          + ", ".join(f"{x:.2g}" for x in tc))
    # 3) supply-temperature input == heat input when they describe the same water
    ha, hb = House(p), House(p)
    for k in range(300):
        t_sup = ha.t_return + (5.0 if k < 120 else 0.0) / p.k_flow
        ra = ha.step(t_out=0.0, t_supply=t_sup, flow_lpm=p.flow_lpm)
        hb.step(t_out=0.0, q_loop=ra.q_loop)
    assert abs(ha.t_slab - hb.t_slab) < 0.02 and abs(ha.t_air - hb.t_air) < 0.02
    # loop: return lies between slab and supply; no flow -> no heat
    h = House(p)
    r = h.step(t_out=0.0, t_supply=35.0)
    assert h.t_slab < r.t_return < 35.0
    h2 = House(p)
    r2 = h2.step(t_out=0.0, t_supply=35.0, flow_lpm=0.0)
    assert abs(r2.q_loop) < 1e-9
    eff = 1 - math.exp(-p.u_ws / p.k_flow)
    print(f"  loop: steady water->slab effectiveness {eff:.2f} at {p.flow_lpm:.0f} L/min "
          f"(return = slab + {1 - eff:.2f} x (supply - slab)); first-minute return {r.t_return:.2f}")
    # 4) sensor: quantized, report-on-change, glow adds in sun
    h = House(p)
    vals = {h.step(t_out=0.0, q_loop=8.0).t_sensor for _ in range(240)}
    assert all(abs(v * 10 - round(v * 10)) < 1e-6 for v in vals)
    hs, hn = House(p), House(p)
    for _ in range(60):
        rs = hs.step(t_out=0.0, ghi=500.0)
        rn = hn.step(t_out=0.0, ghi=0.0)
    print(f"  glow at 500 W/m2 GHI after 1 h: sensor - air {rs.t_sensor_true - rs.t_air:.2f} K; "
          f"real air warming {rs.t_air - rn.t_air:.2f} K")
    # 5) variants: stable, and H follows the variant
    for name, fn in VARIANTS.items():
        v = fn()
        lam = np.linalg.eigvals(matrices(v, "heat")[0]).real
        assert np.all(lam < 0), name
        print(f"  variant {name:13s} H {v.h_total:.3f} kW/K  C_slab {v.c_s:.2f}  "
              f"steady heat for 22 degC at -20/-10/0/+10 degC (no sun): "
              + " / ".join(f"{steady_heat(v, 22.0, t):.2f}" for t in (-20.0, -10.0, 0.0, 10.0)) + " kW")
    pf = flow_scaled(p, 25.0)
    assert abs(pf.h_total / p.h_total - 25 / 29) < 1e-9
    # 6) speed
    h = House(p)
    t0 = time.time()
    for k in range(20000):
        h.step(t_out=0.0, q_loop=4.0 if (k // 120) % 2 else 0.0, poa_s=100.0, hour_local=(k / 60) % 24)
    us = (time.time() - t0) / 20000 * 1e6
    print(f"  speed: {us:.1f} us/step (180 days: {us * 259200 / 1e6:.1f} s)")
    print("house self-check OK")


if __name__ == "__main__":
    _self_check()
