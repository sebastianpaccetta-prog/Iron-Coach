"""Write site/public/data.json - the single file the Next.js site reads."""
import json
from datetime import date, datetime

from .config import ATHLETE_NAME, DIST_LABEL, DIST_M, RACE_DATE, RACE_NAME, SITE_DATA_PATH, SPEED_LABEL


def _activity_card(a):
    dist = (a.get("distance_m") or 0) / DIST_M
    mins = (a.get("duration_s") or 0) / 60
    pace = None
    if a["sport"] == "run" and dist > 0 and mins > 0:
        spd = mins / dist
        pace = f"{int(spd)}:{int((spd % 1) * 60):02d} /{DIST_LABEL}"
    speed = round(dist / (mins / 60), 1) if a["sport"] == "bike" and mins > 0 else None
    return {
        "id": a["id"], "date": a["date"], "start_time": a["start_time"], "sport": a["sport"],
        "name": a.get("name") or a["sport"].capitalize(), "duration_min": round(mins),
        "distance": round(dist, 2), "elevation_m": round(a.get("elevation_m") or 0),
        "avg_hr": a.get("avg_hr"), "max_hr": a.get("max_hr"), "avg_power": a.get("avg_power"),
        "pace": pace, "speed": speed, "rpe": a.get("perceived_exertion"), "tss": a.get("tss"),
    }


def export_site_data(plan, last_week_eval, activities, weekly, load, recovery, recovery_status, zones, this_week_eval=None):
    today = date.today()
    recent_acts = sorted(activities, key=lambda a: (a["date"], a["start_time"]), reverse=True)[:30]
    recovery_series = [
        {"date": d, **m} for d, m in sorted(recovery.items())
        if d >= load[0]["date"]
    ] if load else []
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "athlete": ATHLETE_NAME,
        "units": {"dist": DIST_LABEL, "speed": SPEED_LABEL},
        "race": {"name": RACE_NAME, "date": RACE_DATE.isoformat(), "days_to_race": (RACE_DATE - today).days},
        "zones": zones,
        "this_week": {**plan, "timeline": None, "evaluation": this_week_eval},
        "last_week": last_week_eval,
        "timeline": plan["timeline"],
        "feed": [_activity_card(a) for a in recent_acts],
        "weekly": weekly,
        "load": load,
        "recovery": recovery_series,
        "recovery_status": recovery_status,
        "fitness": {
            "ctl": load[-1]["ctl"] if load else 0, "atl": load[-1]["atl"] if load else 0,
            "tsb": load[-1]["tsb"] if load else 0,
            "ctl_4w_ago": load[-29]["ctl"] if len(load) > 29 else None,
        },
    }
    SITE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    return data
