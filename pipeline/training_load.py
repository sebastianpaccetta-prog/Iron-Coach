"""Training load: per-activity TSS estimates and acute/chronic load tracking.

TSS = hours * IF^2 * 100 where IF (intensity factor) is derived from, in order
of preference: power vs FTP, heart rate vs LTHR, perceived exertion, or a
per-sport default. CTL (fitness) is a 42-day exponentially weighted average,
ATL (fatigue) is 7-day, TSB (form) = CTL - ATL.
"""
from collections import defaultdict
from datetime import date, timedelta

CTL_DAYS = 42
ATL_DAYS = 7
DEFAULT_IF = {"run": 0.75, "bike": 0.70, "swim": 0.70, "strength": 0.60, "other": 0.50}
# Strength/other sessions accumulate less cardio stress than the HR suggests.
SPORT_TSS_SCALE = {"run": 1.0, "bike": 1.0, "swim": 1.0, "strength": 0.6, "other": 0.5}
MAX_WEEKLY_RAMP = 0.10  # no more than 10% week-over-week volume increase


def _if_from_rpe(rpe):
    return 0.5 + 0.05 * max(1.0, min(10.0, rpe))


def activity_tss(a, zones):
    hours = (a.get("duration_s") or 0) / 3600
    if hours <= 0:
        return 0.0
    sport = a["sport"]
    ftp = zones["bike"].get("ftp")
    lthr = zones.get(sport, {}).get("lthr")
    power = a.get("weighted_power") or a.get("avg_power")

    if sport == "bike" and power and ftp:
        intensity = power / ftp
    elif a.get("avg_hr") and lthr:
        intensity = a["avg_hr"] / lthr
    elif a.get("perceived_exertion"):
        intensity = _if_from_rpe(a["perceived_exertion"])
    else:
        intensity = DEFAULT_IF.get(sport, 0.6)
    intensity = max(0.4, min(1.3, intensity))
    return round(hours * intensity ** 2 * 100 * SPORT_TSS_SCALE.get(sport, 1.0), 1)


def daily_tss(activities):
    out = defaultdict(float)
    for a in activities:
        out[a["date"]] += a.get("tss") or 0
    return out


def load_series(activities, end=None, days=120):
    """Return list of {date, tss, ctl, atl, tsb} for the last `days` days."""
    end = end or date.today()
    per_day = daily_tss(activities)
    first = min((a["date"] for a in activities), default=end.isoformat())
    start = min(date.fromisoformat(first), end - timedelta(days=days))
    ctl = atl = 0.0
    kc, ka = 1 / CTL_DAYS, 1 / ATL_DAYS
    series = []
    d = start
    while d <= end:
        t = per_day.get(d.isoformat(), 0.0)
        ctl += (t - ctl) * kc
        atl += (t - atl) * ka
        if d > end - timedelta(days=days):
            series.append({"date": d.isoformat(), "tss": round(t, 1), "ctl": round(ctl, 1),
                           "atl": round(atl, 1), "tsb": round(ctl - atl, 1)})
        d += timedelta(days=1)
    return series


def week_start(d):
    return d - timedelta(days=d.weekday())


def weekly_summary(activities, weeks=16, end=None):
    """Per-week totals by sport: hours, km, tss, sessions."""
    end = end or date.today()
    this_monday = week_start(end)
    buckets = {}
    for i in range(weeks):
        monday = this_monday - timedelta(weeks=i)
        buckets[monday.isoformat()] = {
            "week_start": monday.isoformat(),
            "total_hours": 0.0, "total_tss": 0.0, "sessions": 0,
            "by_sport": {s: {"hours": 0.0, "km": 0.0, "tss": 0.0, "sessions": 0}
                         for s in ("swim", "bike", "run", "strength", "other")},
        }
    for a in activities:
        monday = week_start(date.fromisoformat(a["date"])).isoformat()
        b = buckets.get(monday)
        if not b:
            continue
        s = b["by_sport"][a["sport"]]
        h = (a.get("duration_s") or 0) / 3600
        s["hours"] += h
        s["km"] += (a.get("distance_m") or 0) / 1000
        s["tss"] += a.get("tss") or 0
        s["sessions"] += 1
        b["total_hours"] += h
        b["total_tss"] += a.get("tss") or 0
        b["sessions"] += 1
    out = sorted(buckets.values(), key=lambda b: b["week_start"])
    for b in out:
        b["total_hours"] = round(b["total_hours"], 2)
        b["total_tss"] = round(b["total_tss"], 1)
        for s in b["by_sport"].values():
            s["hours"] = round(s["hours"], 2)
            s["km"] = round(s["km"], 1)
            s["tss"] = round(s["tss"], 1)
    return out


def recovery_status(recovery, end=None):
    """Compare last 7 days of HRV / resting HR / sleep against a 42-day baseline.
    Returns a dict with a `flag` in {good, normal, caution} and reasons."""
    end = end or date.today()
    recent_cut = (end - timedelta(days=7)).isoformat()
    base_cut = (end - timedelta(days=42)).isoformat()

    def avg(metric, lo, hi):
        vals = [m[metric] for d, m in recovery.items() if lo <= d <= hi and metric in m]
        return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)

    hrv_r, n_hrv = avg("hrv", recent_cut, end.isoformat())
    hrv_b, _ = avg("hrv", base_cut, recent_cut)
    rhr_r, n_rhr = avg("resting_hr", recent_cut, end.isoformat())
    rhr_b, _ = avg("resting_hr", base_cut, recent_cut)
    sleep_r, n_sleep = avg("sleep_hours", recent_cut, end.isoformat())
    vo2, _ = avg("vo2max", base_cut, end.isoformat())

    reasons, score = [], 0
    if hrv_r and hrv_b:
        delta = (hrv_r - hrv_b) / hrv_b
        if delta < -0.10:
            score -= 1
            reasons.append(f"HRV down {abs(delta) * 100:.0f}% vs 6-week baseline")
        elif delta > 0.05:
            score += 1
            reasons.append(f"HRV up {delta * 100:.0f}% vs baseline")
    if rhr_r and rhr_b:
        if rhr_r - rhr_b > 4:
            score -= 1
            reasons.append(f"Resting HR up {rhr_r - rhr_b:.0f} bpm vs baseline")
        elif rhr_b - rhr_r > 2:
            score += 1
            reasons.append("Resting HR below baseline")
    if sleep_r and n_sleep >= 3:
        if sleep_r < 6.5:
            score -= 1
            reasons.append(f"Sleep averaging {sleep_r:.1f} h")
        elif sleep_r >= 7.5:
            reasons.append(f"Sleep averaging {sleep_r:.1f} h")

    flag = "caution" if score < 0 else ("good" if score > 0 else "normal")
    if not reasons:
        reasons.append("No strong recovery signal either way")
    return {
        "flag": flag, "reasons": reasons,
        "hrv_7d": round(hrv_r, 1) if hrv_r else None,
        "hrv_42d": round(hrv_b, 1) if hrv_b else None,
        "resting_hr_7d": round(rhr_r, 1) if rhr_r else None,
        "resting_hr_42d": round(rhr_b, 1) if rhr_b else None,
        "sleep_7d": round(sleep_r, 1) if sleep_r else None,
        "vo2max": round(vo2, 1) if vo2 else None,
    }
