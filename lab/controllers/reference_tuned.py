"""Ranking baseline: the reference controller aimed so that the mean room air of the scenario is
on target (stdlib only).

The offset `ref_target_offset` is found per scenario, variant, seed and outage rate by
lab/sim/ranking.py:tuned_offset (secant on the mean true air, tolerance 0.03 K) and passed in as a
parameter; without it this is the reference controller with the baseline gains.

Review round 1 (m4): the plain reference held comfort loosely (mean air 21.9-22.3 degC by week),
so 'beats the reference' partly meant 'tracks the room differently'.

Review round 2 (N2): the gains were chosen from a family of tuned references over the season
(validate_sim `comfort`, 4 seeds): kp 3 K of water per K of room error and ki 0.3 K per K-hour
beat the plain reference's kp 2 / ki 0.15 on both energy (-0.4 %) and comfort (mean |error| 0.510
vs 0.515 K) with fewer starts; higher gains save a little more energy only by holding the room
less tightly. Setpoints are clamped to 25-45 degC (review round 2, N8).
"""
from __future__ import annotations

from lab.controllers.reference import ReferenceController

BASELINE_KP = 3.0
BASELINE_KI_PER_H = 0.3


class ReferenceTuned(ReferenceController):
    name = "reference_tuned"

    def reset(self, params: dict) -> None:
        p = dict(params)
        p.setdefault("ref_kp", BASELINE_KP)
        p.setdefault("ref_ki_per_h", BASELINE_KI_PER_H)
        super().reset(p)


CONTROLLER = ReferenceTuned
