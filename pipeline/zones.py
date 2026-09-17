"""Estimate heart-rate / pace zones from the athlete's own history.

Lactate threshold HR (LTHR) is estimated as the average of the three highest
average-HR efforts lasting 20-70 minutes in the last 6 months; if that is not
available we fall back to 90% of the highest observed max HR. Zones follow the
common 5-zone LTHR model (Friel).
"""
from datetime import date, timedelta

from .config import DIST_LABEL, DIST_M

LTHR_ZONE_PCTS = [
    ("Z1", "Recovery", 0.00, 0.85),
    ("Z2", "Aerobic / Endurance", 0.85, 0.89),
    ("Z3", "Tempo", 0.90, 0.94),
    ("Z4", "Threshold", 0.95, 0.99),
    ("Z5", "VO2max", 1.00, 1.10),
]
# Run threshold pace zones as a fraction of threshold speed (faster = higher fraction)
PACE_ZONE_PCTS = [("Z1", 0.70, 0.79), ("Z2", 0.79, 0.87), ("Z3", 0.87, 0.94), ("Z4", 0.94, 1.01), ("Z5", 1.01, 1.12)]

DEFAULT_MAX_HR = 185  # only used if there is no HR data at all
BIKE_LTHR_OFFSET = -5  # bike LTHR is typically a few bpm below run LTHR


def _recent(activities, months=6):
    cutoff = (date.today() - timedelta(days=30 * months)).isoformat()
    return [a for a in activities if a["date"] >= cutoff]


def estimate_lthr(activities, sport):
    """Average of the top-3 avg HR efforts lasting 20-70 min."""
    cands = [
        a["avg_hr"] for a in _recent(activities)
        if a["sport"] == sport and a.get("avg_hr") and a.get("duration_s")
        and 1200 <= a["duration_s"] <= 4200
    ]
    if len(cands) < 2:
        cands = [
            a["avg_hr"] for a in activities
            if a["sport"] == sport and a.get("avg_hr") and a.get("duration_s")
            and 1200 <= a["duration_s"] <= 4200
        ]
    if not cands:
        return None
    top = sorted(cands, reverse=True)[:3]
    return round(sum(top) / len(top))


def estimate_max_hr(activities):
    vals = sorted((a["max_hr"] for a in activities if a.get("max_hr")), reverse=True)
    if not vals:
        return DEFAULT_MAX_HR
    # Ignore the single highest reading in case of a sensor spike.
    return round(vals[1] if len(vals) > 1 else vals[0])


def estimate_threshold_speed(activities):
    """Best average run speed (m/s) over 20-70 min in the last 6 months."""
    cands = [
        a["avg_speed_mps"] for a in _recent(activities)
        if a["sport"] == "run" and a.get("avg_speed_mps") and a.get("duration_s")
        and 1200 <= a["duration_s"] <= 4200
    ]
    if not cands:
        return None
    top = sorted(cands, reverse=True)[:3]
    return sum(top) / len(top)


def estimate_ftp(activities):
    cands = [
        a["weighted_power"] or a["avg_power"] for a in _recent(activities, 12)
        if a["sport"] == "bike" and (a.get("weighted_power") or a.get("avg_power"))
        and a.get("duration_s") and a["duration_s"] >= 1200
    ]
    if len(cands) < 3:
        return None
    return round(0.95 * sorted(cands, reverse=True)[0])


def _hr_zones(lthr):
    return [
        {"zone": z, "name": n, "low": round(lthr * lo), "high": round(lthr * hi)}
        for z, n, lo, hi in LTHR_ZONE_PCTS
    ]


def _fmt_pace(speed_mps):
    """m/s -> 'm:ss' per DIST_M (mile or km, see config.UNITS)."""
    if not speed_mps:
        return None
    sec = DIST_M / speed_mps
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def build_zones(activities, resting_hr=None):
    max_hr = estimate_max_hr(activities)
    run_lthr = estimate_lthr(activities, "run") or round(max_hr * 0.90)
    bike_lthr = estimate_lthr(activities, "bike") or (run_lthr + BIKE_LTHR_OFFSET)
    thr_speed = estimate_threshold_speed(activities)
    ftp = estimate_ftp(activities)

    pace_zones = None
    if thr_speed:
        pace_zones = [
            {"zone": z, "fast": _fmt_pace(thr_speed * hi), "slow": _fmt_pace(thr_speed * lo)}
            for z, lo, hi in PACE_ZONE_PCTS
        ]

    return {
        "max_hr": max_hr,
        "resting_hr": resting_hr,
        "run": {"lthr": run_lthr, "hr_zones": _hr_zones(run_lthr),
                "threshold_pace": _fmt_pace(thr_speed), "pace_zones": pace_zones,
                "pace_unit": DIST_LABEL},
        "bike": {"lthr": bike_lthr, "hr_zones": _hr_zones(bike_lthr), "ftp": ftp},
        "swim": {"note": "Use RPE: Z2 = conversational, Z4 = hard but repeatable"},
    }
