"""Central configuration for Iron Coach. Tweak race date and paths here."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RACE_DATE = date(2027, 2, 1)
RACE_NAME = "Half Ironman 70.3"
ATHLETE_NAME = "Sebastian"

# Units for run pace, bike speed and distances: "imperial" (min/mi, mph, mi)
# or "metric" (min/km, km/h, km). Swim pace is always per 100 m.
UNITS = "imperial"
MILE_M = 1609.344
DIST_M = MILE_M if UNITS == "imperial" else 1000.0
DIST_LABEL = "mi" if UNITS == "imperial" else "km"
SPEED_LABEL = "mph" if UNITS == "imperial" else "km/h"

# Goal finish time in hours. Race-pace targets in the plan are derived from it.
GOAL_TIME_H = 5.0
# Reference split for a 5:00 70.3 (swim/T1/bike/T2/run, minutes). Scaled to GOAL_TIME_H.
REFERENCE_SPLITS_MIN = {"swim": 35, "t1": 4, "bike": 156, "t2": 3, "run": 102}
SWIM_M, BIKE_M, RUN_M = 1900, 90_000, 21_100

# Biggest training week, chosen inside this range from your current fitness
# (see plan.peak_week_hours). 11 h is the floor for a sub-5 70.3, 14 h the ceiling.
PEAK_WEEK_HOURS_RANGE = (11.0, 14.0)

DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "normalized.db"

# Export folders. Any of these locations work; whichever holds the most recently
# modified key file (activities.csv / export.xml) is used, so dropping in a new
# export always wins regardless of folder name. See HOW_TO_UPDATE.md.
STRAVA_DIR_CANDIDATES = [DATA_DIR / "strava"] + list(ROOT.glob("strava_export*")) + list(DATA_DIR.glob("strava_export*"))
APPLE_HEALTH_DIR_CANDIDATES = ([DATA_DIR / "apple_health"] + list(ROOT.glob("apple_health_export*"))
                               + list(DATA_DIR.glob("apple_health_export*")))
STRAVA_KEY_FILE = "activities.csv"
APPLE_HEALTH_KEY_FILE = "export.xml"

SITE_DATA_PATH = ROOT / "site" / "public" / "data.json"
PLAN_OUTPUT_PATH = DATA_DIR / "plan.json"

GOOGLE_CREDENTIALS_PATH = ROOT / "credentials.json"
GOOGLE_TOKEN_PATH = ROOT / "token.json"
CALENDAR_NAME = "Iron Coach"


def goal_splits(goal_h=GOAL_TIME_H):
    """Scale the reference split to the goal time. Returns minutes per leg plus
    the pace each leg implies (swim s/100m, bike speed and run s/unit in UNITS)."""
    scale = goal_h * 60 / sum(REFERENCE_SPLITS_MIN.values())
    mins = {k: v * scale for k, v in REFERENCE_SPLITS_MIN.items()}
    return {
        **{k: round(v) for k, v in mins.items()},
        "swim_s_per_100m": round(mins["swim"] * 60 / (SWIM_M / 100)),
        "bike_speed": round((BIKE_M / DIST_M) / (mins["bike"] / 60), 1),
        "run_s_per_dist": round(mins["run"] * 60 / (RUN_M / DIST_M)),
    }


def find_dir(candidates, key_file=None):
    """Return the candidate directory containing `key_file` whose copy of it was
    modified most recently. Apple's zip nests export.xml one level down
    (apple_health_export/export.xml), so one level of nesting is tolerated.
    Without key_file, the first existing directory wins."""
    if key_file is None:
        return next((c for c in candidates if c.is_dir()), None)
    best, best_mtime = None, -1
    for c in candidates:
        if not c.is_dir():
            continue
        for f in [c / key_file] + list(c.glob(f"*/{key_file}")):
            if f.is_file() and f.stat().st_mtime > best_mtime:
                best, best_mtime = f.parent, f.stat().st_mtime
    return best
