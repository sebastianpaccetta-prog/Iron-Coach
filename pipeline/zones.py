"""Heart-rate / pace zones from the athlete's own history.

HR zones (McMillan, "How to calculate heart rate zones"), same for run and bike:
- Heart rate reserve (Karvonen): resting HR + % x (max HR - resting HR). Used whenever
  a resting HR is known (7-day average from Apple Health).
- Age-based: % of max HR. Fallback when there is no resting HR.
Max HR, in order: MAX_HR in config.py, your recorded history (second highest max,
aged), 220 - age.

LTHR is estimated separately because training load (hrTSS) needs it:
1. LTHR_OVERRIDE in config.py - a tested value (Friel 30-min solo test).
2. The best 20-min HR stretch inside any run (or ride) of 30+ min in the last
   18 months. Training runs only ever under-estimate it, so it is used as
   a floor, never averaged down with easier runs.
3. LTHR_PCT_OF_MAX of max HR, when no effort in the window beats it. Trained
   runners reach threshold at ~85-92% of max HR, so 88% is a middle estimate.
Bike LTHR uses the same rules with run LTHR + BIKE_LTHR_OFFSET as its floor.
"""
from datetime import date, timedelta

from .config import DIST_LABEL, DIST_M, LTHR_OVERRIDE, MAX_HR

# Five bands, as a fraction of heart rate reserve (Karvonen) or, without resting HR, of max HR
ZONE_PCTS = [
    ("Z1", "Recovery", 0.50, 0.60),
    ("Z2", "Aerobic / Endurance", 0.60, 0.70),
    ("Z3", "Tempo", 0.70, 0.80),
    ("Z4", "Threshold", 0.80, 0.90),
    ("Z5", "VO2max", 0.90, 1.00),
]
METHOD_LABEL = {"age": "Age-based (% of max HR)", "hrr": "Heart rate reserve (Karvonen)"}
# Run threshold pace zones as a fraction of threshold speed (faster = higher fraction)
PACE_ZONE_PCTS = [("Z1", 0.70, 0.79), ("Z2", 0.79, 0.87), ("Z3", 0.87, 0.94), ("Z4", 0.94, 1.01), ("Z5", 1.01, 1.12)]

DEFAULT_MAX_HR = 185  # only used with no HR data and no date of birth
BIKE_LTHR_OFFSET = -5  # bike LTHR is typically a few bpm below run LTHR
EFFORT_LOOKBACK_DAYS = 548  # 18 months: LTHR moves much less with fitness than pace does
MIN_EFFORT_S = 1800  # a 20-min stretch inside 30+ min matches the Friel test
LTHR_PCT_OF_MAX = 0.88
MAX_HR_DECLINE_PER_YEAR = 0.7  # Tanaka et al. 2001: HRmax ~ 208 - 0.7 x age


def _recent(activities, months=6):
    cutoff = (date.today() - timedelta(days=30 * months)).isoformat()
    return [a for a in activities if a["date"] >= cutoff]


def estimate_max_hr(activities, age=None):
    """(max HR, where it came from). History: each activity's max HR is aged by
    MAX_HR_DECLINE_PER_YEAR, then the second highest is used in case the highest
    is a sensor spike."""
    if MAX_HR:
        return MAX_HR, "set in config.py"
    today = date.today()
    vals = sorted(
        ((a["max_hr"] - MAX_HR_DECLINE_PER_YEAR * (today - date.fromisoformat(a["date"])).days / 365.25, a)
         for a in activities if a.get("max_hr")),
        key=lambda v: v[0], reverse=True)
    if vals:
        v, a = vals[1] if len(vals) > 1 else vals[0]
        return round(v), f"{a['max_hr']:.0f} bpm on {a['date']}, aged to today"
    if age:
        return 220 - age, f"220 - age {age}"
    return DEFAULT_MAX_HR, "default (no HR data or age)"


def best_effort(activities, sport):
    """The activity with the highest 20-min HR among 30+ min efforts in the lookback window."""
    cutoff = (date.today() - timedelta(days=EFFORT_LOOKBACK_DAYS)).isoformat()
    efforts = [a for a in activities
               if a["sport"] == sport and a.get("best20_hr") and (a.get("duration_s") or 0) >= MIN_EFFORT_S
               and a["date"] >= cutoff]
    return max(efforts, key=lambda a: a["best20_hr"], default=None)


def estimate_lthr(activities, sport, floor, floor_source):
    """(LTHR, where it came from). The best 20-min effort wins if it beats `floor`."""
    if LTHR_OVERRIDE.get(sport):
        return LTHR_OVERRIDE[sport], "tested, set in config.py"
    best = best_effort(activities, sport)
    if best and best["best20_hr"] >= floor:
        return round(best["best20_hr"]), f"best 20 min of \"{best['name']}\" on {best['date']}"
    note = (f"; best 20 min in 18 months was {best['best20_hr']:.0f} bpm on {best['date']}" if best
            else "; no 30+ min effort with HR in 18 months")
    return floor, f"estimated from {floor_source}{note} - do a 30-min test to pin it down"


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


def hr_zones(max_hr, resting_hr=None):
    """(method, zones, where they came from): heart rate reserve if resting HR is known, else % of max HR."""
    rest = resting_hr or 0
    zones = [
        {"zone": z, "name": n, "low": round(rest + lo * (max_hr - rest)), "high": round(rest + hi * (max_hr - rest))}
        for z, n, lo, hi in ZONE_PCTS
    ]
    if resting_hr:
        return "hrr", zones, f"max HR {max_hr}, resting HR {round(resting_hr)} (7-day avg)"
    return "age", zones, f"max HR {max_hr}; no resting HR yet"


def _fmt_pace(speed_mps):
    """m/s -> 'm:ss' per DIST_M (mile or km, see config.UNITS)."""
    if not speed_mps:
        return None
    sec = DIST_M / speed_mps
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def build_zones(activities, resting_hr=None, age=None):
    max_hr, max_hr_source = estimate_max_hr(activities, age)
    method, zones, zones_source = hr_zones(max_hr, resting_hr)
    run_lthr, run_source = estimate_lthr(activities, "run", round(max_hr * LTHR_PCT_OF_MAX),
                                         f"{LTHR_PCT_OF_MAX:.0%} of max HR {max_hr}")
    bike_lthr, bike_source = estimate_lthr(activities, "bike", run_lthr + BIKE_LTHR_OFFSET,
                                           f"run LTHR {run_lthr} {BIKE_LTHR_OFFSET:+d}")
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
        "max_hr_source": max_hr_source,
        "age": age,
        "resting_hr": resting_hr,
        "method": method,
        "method_label": METHOD_LABEL[method],
        "zones_source": zones_source,
        "run": {"lthr": run_lthr, "lthr_source": run_source, "hr_zones": zones,
                "threshold_pace": _fmt_pace(thr_speed), "pace_zones": pace_zones, "pace_unit": DIST_LABEL},
        "bike": {"lthr": bike_lthr, "lthr_source": bike_source, "hr_zones": zones, "ftp": ftp},
        "swim": {"note": "Use RPE: Z2 = conversational, Z4 = hard but repeatable"},
    }
