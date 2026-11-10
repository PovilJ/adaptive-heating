// Adaptive Heating chart card (custom:adaptive-heating-chart). No dependencies.
//
// Values never float under the pointer: the row above the plot shows every series' value at the
// cursor (live values when idle). Hover with a mouse; on a phone tap or drag sideways (vertical
// drags still scroll the page). Pointer position is mapped through the plot's on-screen box, so
// the cursor sits where the finger or mouse is even inside scaled or transformed cards.
//
// type: custom:adaptive-heating-chart
// title: Floor · 24 h
// hours: 24                 # window; bars: days = hours / 24
// height: 170
// bars: false               # true: one bar per day from long-term statistics ("change")
// series:
//   - entity: sensor.x      # required
//     name: Floor
//     color: "#ff8a65"
//     attribute: temperature   # optional: plot an attribute instead of the state
//     step: true               # hold each value until the next change (setpoints, targets)
//     dashed: true
//     fill: true               # soft area under the line
//     offset: -1.4             # plot value + offset (e.g. a band around a target)
//     unit: "°C"
// shade:                     # optional: background spans while an entity is in given states
//   entity: sensor.unit_status
//   states: [HEAT]
//   name: Heating
//   color: "#ff9800"

const REFRESH_MS = 5 * 60 * 1000;
const PAD = { l: 34, r: 8, t: 6, b: 18 };
const NS = "http://www.w3.org/2000/svg";

const el = (tag, attrs = {}, parent) => {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
};
const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? null : Number(v));
const seconds = (v) => (typeof v === "number" ? v : parseFloat(v));

// Last point at or before t (history holds changes, so that is the value then).
function valueAt(points, t) {
  let lo = 0, hi = points.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (points[mid][0] <= t) { found = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return found < 0 ? null : points[found][1];
}

class AdaptiveHeatingChart extends HTMLElement {
  setConfig(config) {
    if (!Array.isArray(config.series) || !config.series.length) throw new Error("series is required");
    this._config = { hours: 24, height: 170, ...config };
    this._data = null;
    this._fetched = 0;
    if (this._root) this._root.innerHTML = "";
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    if (Date.now() - this._fetched > REFRESH_MS) this._fetch();
    else if (this._cursor === null) this._readout(null);
  }

  getCardSize() { return 4; }
  getGridOptions() { return { columns: 12, min_columns: 6, rows: "auto" }; }

  _build() {
    this._built = true;
    this._cursor = null;
    if (!this._root) this._root = this.attachShadow({ mode: "open" });
    const c = this._config;
    this._root.innerHTML = `
      <style>
        ha-card { padding: 12px 12px 8px; overflow: hidden; }
        .head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
        .title { font-size: 15px; font-weight: 500; color: var(--primary-text-color); }
        .when { font-size: 12px; color: var(--secondary-text-color); white-space: nowrap; }
        .vals { display: flex; flex-wrap: wrap; gap: 2px 14px; margin: 4px 0 6px; min-height: 22px; }
        .v { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
        .v b { font-size: 16px; font-weight: 600; color: var(--primary-text-color); margin-left: 3px; }
        .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
        .plot { position: relative; touch-action: pan-y; user-select: none; -webkit-user-select: none;
                -webkit-tap-highlight-color: transparent; cursor: crosshair; }
        svg { display: block; width: 100%; overflow: visible; }
        .axis { font-size: 10px; fill: var(--secondary-text-color); }
        .grid { stroke: var(--divider-color, rgba(127,127,127,.25)); stroke-width: 1; }
        .msg { font-size: 12px; fill: var(--secondary-text-color); }
      </style>
      <ha-card>
        <div class="head"><span class="title"></span><span class="when"></span></div>
        <div class="vals"></div>
        <div class="plot"><svg height="${c.height}"></svg></div>
      </ha-card>`;
    this._root.querySelector(".title").textContent = c.title || "";
    this._svg = this._root.querySelector("svg");
    this._plot = this._root.querySelector(".plot");
    this._when = this._root.querySelector(".when");
    this._vals = this._root.querySelector(".vals");

    const at = (ev) => {
      const box = this._svg.getBoundingClientRect();
      if (!box.width) return null;
      const x = ((ev.clientX - box.left) / box.width) * this._w;  // on-screen box -> drawing units
      const f = (x - PAD.l) / (this._w - PAD.l - PAD.r);
      return f < 0 || f > 1 ? null : this._t0 + f * (this._t1 - this._t0);
    };
    const show = (ev) => { clearTimeout(this._release); this._setCursor(at(ev)); };
    const hide = (delay) => {
      clearTimeout(this._release);
      this._release = setTimeout(() => this._setCursor(null), delay);
    };
    this._plot.addEventListener("pointermove", (ev) => {
      if (ev.pointerType === "mouse" || ev.buttons || ev.pressure > 0) show(ev);
    });
    this._plot.addEventListener("pointerdown", show);
    this._plot.addEventListener("pointerup", (ev) => { if (ev.pointerType !== "mouse") hide(4000); });
    this._plot.addEventListener("pointercancel", () => hide(0));   // the page took the gesture (scroll)
    this._plot.addEventListener("pointerleave", (ev) => { if (ev.pointerType === "mouse") hide(0); });
    new ResizeObserver(() => this._draw()).observe(this._plot);
  }

  async _fetch() {
    const hass = this._hass, c = this._config;
    if (!hass || this._loading) return;
    this._loading = true;
    this._fetched = Date.now();
    this._window();
    const end = new Date(), start = new Date(this._t0 * 1000);
    try {
      const data = {};
      if (c.bars) {
        const ids = c.series.map((s) => s.entity);
        const r = await hass.callWS({ type: "recorder/statistics_during_period", start_time: start.toISOString(),
          end_time: end.toISOString(), statistic_ids: ids, period: "day", types: ["change"] });
        for (const s of c.series) {
          data[s.entity] = (r[s.entity] || []).map((row) => {
            const t = row.start > 1e11 ? row.start / 1000 : row.start;
            return [t, num(row.change)];
          });
        }
      } else {
        const plain = new Set(), withAttrs = new Set();
        for (const s of c.series) (s.attribute ? withAttrs : plain).add(s.entity);
        if (c.shade) plain.add(c.shade.entity);
        const ask = (ids, attrs) => ids.size ? hass.callWS({ type: "history/history_during_period",
          start_time: start.toISOString(), end_time: end.toISOString(), entity_ids: [...ids],
          include_start_time_state: true, significant_changes_only: false,
          minimal_response: !attrs, no_attributes: !attrs }) : Promise.resolve({});
        const [a, b] = await Promise.all([ask(plain, false), ask(withAttrs, true)]);
        for (const s of c.series) {
          const rows = (s.attribute ? b : a)[s.entity] || [];
          const off = s.offset || 0;
          const pts = [];
          for (const row of rows) {
            const raw = s.attribute ? (row.a || {})[s.attribute] : row.s;
            const v = num(raw);
            pts.push([seconds(row.lu ?? row.lc), v === null ? null : v + off]);
          }
          data[s.entity + "|" + (s.attribute || "") + "|" + off] = pts;
        }
        if (c.shade) data.__shade = (a[c.shade.entity] || []).map((row) => [seconds(row.lu ?? row.lc), row.s]);
      }
      this._data = data;
      this._error = null;
    } catch (err) {
      this._error = (err && err.message) || "History unavailable";
    }
    this._loading = false;
    this._draw();
  }

  _window() {
    // Bars end at the next local midnight, so each bar is one local day.
    const midnight = new Date();
    midnight.setHours(24, 0, 0, 0);
    this._t1 = this._config.bars ? midnight / 1000 : Date.now() / 1000;
    this._t0 = this._t1 - this._config.hours * 3600;
  }

  _key(s) { return this._config.bars ? s.entity : s.entity + "|" + (s.attribute || "") + "|" + (s.offset || 0); }

  _unit(s) {
    if (s.unit !== undefined) return s.unit;
    const st = this._hass && this._hass.states[s.entity];
    return (st && st.attributes.unit_of_measurement) || "";
  }

  _live(s) {
    const st = this._hass && this._hass.states[s.entity];
    if (!st) return null;
    const v = num(s.attribute ? st.attributes[s.attribute] : st.state);
    return v === null ? null : v + (s.offset || 0);
  }

  _draw() {
    const c = this._config, svg = this._svg;
    if (!svg) return;
    this._w = Math.max(this._plot.clientWidth, 120);
    const W = this._w, H = c.height;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.innerHTML = "";
    const now = Date.now() / 1000;
    this._window();
    if (!this._data) {
      el("text", { x: W / 2, y: H / 2, "text-anchor": "middle", class: "msg" }, svg).textContent =
        this._error || "Loading…";
      this._readout(null);
      return;
    }
    const x = (t) => PAD.l + ((t - this._t0) / (this._t1 - this._t0)) * (W - PAD.l - PAD.r);
    // y range from what is visible
    let lo = Infinity, hi = -Infinity;
    for (const s of c.series) {
      for (const [t, v] of this._data[this._key(s)] || []) {
        if (v !== null && t >= this._t0 - 86400) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
      }
    }
    if (c.bars) lo = Math.min(lo, 0);
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (c.min !== undefined) lo = c.min;
    if (c.max !== undefined) hi = c.max;
    if (hi - lo < 1) { const m = (hi + lo) / 2; lo = m - 0.5; hi = m + 0.5; }
    const span = hi - lo;
    if (!c.bars) { lo -= span * 0.08; hi += span * 0.08; }
    const y = (v) => PAD.t + (1 - (v - lo) / (hi - lo)) * (H - PAD.t - PAD.b);
    this._x = x; this._y = y;

    // shaded spans
    if (c.shade && this._data.__shade) {
      const want = new Set((c.shade.states || []).map(String));
      const rows = this._data.__shade;
      for (let i = 0; i < rows.length; i++) {
        if (!want.has(String(rows[i][1]))) continue;
        const a = Math.max(rows[i][0], this._t0), b = Math.min(i + 1 < rows.length ? rows[i + 1][0] : now, this._t1);
        if (b > a) el("rect", { x: x(a), y: PAD.t, width: Math.max(x(b) - x(a), 1), height: H - PAD.t - PAD.b,
          fill: c.shade.color || "#ff9800", "fill-opacity": 0.12 }, svg);
      }
    }
    // grid + y labels at round numbers (about three lines)
    const raw = (hi - lo) / 3, mag = 10 ** Math.floor(Math.log10(raw));
    const tick = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((m) => m >= raw);
    for (let v = Math.ceil(lo / tick) * tick; v <= hi + 1e-9; v += tick) {
      const yy = y(v);
      el("line", { x1: PAD.l, x2: W - PAD.r, y1: yy, y2: yy, class: "grid" }, svg);
      el("text", { x: PAD.l - 4, y: yy + 3, "text-anchor": "end", class: "axis" }, svg).textContent =
        Number.isInteger(Math.round(v * 1e6) / 1e6) ? v.toFixed(0) : v.toFixed(1);
    }
    // x labels
    const step = c.bars || c.hours > 72 ? 86400 : c.hours > 30 ? 12 * 3600 : 6 * 3600;
    const tz = -new Date().getTimezoneOffset() * 60;
    for (let t = Math.ceil((this._t0 + tz) / step) * step - tz; t <= this._t1; t += step) {
      const d = new Date(t * 1000);
      const label = step >= 86400 ? d.toLocaleDateString(undefined, { weekday: "short" })
        : d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
      const xx = c.bars ? x(t + 43200) : x(t);
      if (xx < PAD.l + 10 || xx > W - PAD.r - 10) continue;
      el("text", { x: xx, y: H - 4, "text-anchor": "middle", class: "axis" }, svg).textContent = label;
    }
    // series
    c.series.forEach((s, i) => {
      const pts = (this._data[this._key(s)] || []).filter(([t]) => t <= this._t1);
      const color = s.color || `hsl(${(i * 67) % 360} 70% 55%)`;
      if (c.bars) {
        const bw = Math.max(((W - PAD.l - PAD.r) / (c.hours / 24)) * 0.6 / c.series.length, 2);
        for (const [t, v] of pts) {
          if (v === null || t < this._t0) continue;
          const cx = x(t + 43200) + (i - (c.series.length - 1) / 2) * bw;
          el("rect", { x: cx - bw / 2, y: y(Math.max(v, 0)), width: bw, height: Math.abs(y(v) - y(0)), rx: 2,
            fill: color, "fill-opacity": 0.85 }, svg);
        }
        return;
      }
      // Downsample to about one point per pixel (mean per column) unless stepped.
      let prev = null, col = null, sum = 0, n = 0;
      const path = [];
      const segs = [];
      const flush = () => { if (path.length) segs.push(path.splice(0)); col = null; };
      for (let k = 0; k < pts.length; k++) {
        let [t, v] = pts[k];
        if (t < this._t0) { if (k + 1 < pts.length && pts[k + 1][0] > this._t0) t = this._t0; else continue; }
        if (v === null) { flush(); prev = null; continue; }
        const xx = Math.round(x(t));
        if (s.step) {
          if (prev !== null) path.push([xx, y(prev)]);
          path.push([xx, y(v)]);
          prev = v;
        } else {
          if (xx === col) { sum += v; n += 1; path[path.length - 1] = [xx, y(sum / n)]; }
          else { col = xx; sum = v; n = 1; path.push([xx, y(v)]); }
        }
      }
      // carry the last value to now
      const last = pts.length ? pts[pts.length - 1][1] : null;
      if (last !== null && path.length) path.push([x(Math.min(now, this._t1)), y(last)]);
      flush();
      for (const seg of segs) {
        const d = seg.map(([a, b], j) => (j ? "L" : "M") + a.toFixed(1) + " " + b.toFixed(1)).join("");
        if (s.fill) {
          el("path", { d: d + `L${seg[seg.length - 1][0]} ${H - PAD.b}L${seg[0][0]} ${H - PAD.b}Z`,
            fill: color, "fill-opacity": 0.12, stroke: "none" }, svg);
        }
        el("path", { d, fill: "none", stroke: color, "stroke-width": s.dashed ? 1.5 : 2,
          "stroke-dasharray": s.dashed ? "4 4" : "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      }
    });
    // cursor layer
    this._cur = el("g", { visibility: "hidden" }, svg);
    el("line", { y1: PAD.t, y2: H - PAD.b, stroke: "var(--primary-text-color)", "stroke-opacity": 0.5,
      "stroke-width": 1 }, this._cur);
    this._dots = c.series.map((s, i) => el("circle", { r: 4, fill: s.color || `hsl(${(i * 67) % 360} 70% 55%)`,
      stroke: "var(--card-background-color, #fff)", "stroke-width": 2 }, this._cur));
    this._setCursor(this._cursor);
  }

  _setCursor(t) {
    if (t !== null && this._config.bars) t = this._t0 + Math.floor((t - this._t0) / 86400) * 86400 + 1;  // snap to the day
    this._cursor = t;
    if (!this._cur) return this._readout(t);
    if (t === null || !this._data) {
      this._cur.setAttribute("visibility", "hidden");
      return this._readout(null);
    }
    const xx = this._config.bars ? this._x(t + 43199) : this._x(t);
    this._cur.setAttribute("visibility", "visible");
    this._cur.firstChild.setAttribute("x1", xx);
    this._cur.firstChild.setAttribute("x2", xx);
    this._config.series.forEach((s, i) => {
      const v = valueAt(this._data[this._key(s)] || [], t);
      const dot = this._dots[i];
      if (v === null || this._config.bars) dot.setAttribute("visibility", "hidden");
      else { dot.setAttribute("visibility", "visible"); dot.setAttribute("cx", xx); dot.setAttribute("cy", this._y(v)); }
    });
    this._readout(t);
  }

  _readout(t) {
    const c = this._config;
    if (!this._vals) return;
    const parts = [];
    c.series.forEach((s, i) => {
      let v;
      if (t === null) v = c.bars ? (this._data && (this._data[s.entity] || []).slice(-1)[0] || [0, null])[1] : this._live(s);
      else v = this._data ? valueAt(this._data[this._key(s)] || [], t) : null;
      const digits = s.digits ?? 1;
      const text = v === null || v === undefined ? "—" : v.toFixed(digits) + (this._unit(s) ? " " + this._unit(s) : "");
      parts.push(`<span class="v"><span class="dot" style="background:${s.color || `hsl(${(i * 67) % 360} 70% 55%)`}"></span>` +
        `${s.name || s.entity}<b>${text}</b></span>`);
    });
    if (c.shade) {
      let st;
      if (t === null) st = this._hass && this._hass.states[c.shade.entity] && this._hass.states[c.shade.entity].state;
      else st = this._data && valueAt(this._data.__shade || [], t);
      const on = (c.shade.states || []).map(String).includes(String(st));
      parts.push(`<span class="v"><span class="dot" style="background:${c.shade.color || "#ff9800"};opacity:${on ? 0.8 : 0.2}"></span>` +
        `${c.shade.name || "Active"}<b>${on ? "on" : "off"}</b></span>`);
    }
    this._vals.innerHTML = parts.join("");
    if (t === null) this._when.textContent = c.bars ? "latest day" : "now";
    else {
      const d = new Date(t * 1000);
      this._when.textContent = c.bars ? d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })
        : d.toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" });
    }
  }
}

if (!customElements.get("adaptive-heating-chart")) {
  customElements.define("adaptive-heating-chart", AdaptiveHeatingChart);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "adaptive-heating-chart", name: "Adaptive Heating chart",
    description: "History chart with values above the plot instead of a floating tooltip." });
}
