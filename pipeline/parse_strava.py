"""Parse Strava bulk export activities.csv into normalized activity rows.

Only activities.csv is read. The raw .fit/.gpx files and the ~40 social/profile
CSVs in the export are ignored - the summary CSV already carries everything the
plan needs (duration, distance, HR, power, elevation, RPE).
"""
import csv
from datetime import datetime, timezone

from .config import STRAVA_DIR_CANDIDATES, STRAVA_KEY_FILE, find_dir

SPORT_MAP = {
    "run": "run", "trailrun": "run", "virtualrun": "run", "treadmill": "run",
    "ride": "bike", "virtualride": "bike", "ebikeride": "bike", "gravelride": "bike",
    "mountainbikeride": "bike", "handcycle": "bike",
    "swim": "swim", "openwaterswim": "swim",
    "workout": "strength", "weighttraining": "strength", "crossfit": "strength",
    "hiit": "strength", "yoga": "strength", "pilates": "strength",
}

# Strava's CSV has several duplicated header names (e.g. "Distance" in km and in
# metres). We keep every column index per name and take the last non-empty one,
# which is always the metric/detailed version.


def _index_headers(header):
    idx = {}
    for i, h in enumerate(header):
        idx.setdefault(h.strip(), []).append(i)
    return idx


def _get(row, idx, name):
    for i in reversed(idx.get(name, [])):
        if i < len(row) and row[i].strip() != "":
            return row[i].strip()
    return None


def _num(v):
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _parse_date(s):
    # Strava exports "Sep 14, 2026, 12:02:29 AM" in UTC.
    dt = datetime.strptime(s, "%b %d, %Y, %I:%M:%S %p").replace(tzinfo=timezone.utc)
    return dt.astimezone()


def normalize_sport(raw_type):
    key = (raw_type or "").replace(" ", "").lower()
    return SPORT_MAP.get(key, "other")


def parse_activities_csv(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        idx = _index_headers(header)
        for row in reader:
            if not row or not _get(row, idx, "Activity Date"):
                continue
            local = _parse_date(_get(row, idx, "Activity Date"))
            raw_type = _get(row, idx, "Activity Type")
            moving = _num(_get(row, idx, "Moving Time"))
            elapsed = _num(_get(row, idx, "Elapsed Time"))
            rows.append({
                "source_id": _get(row, idx, "Activity ID"),
                "date": local.date().isoformat(),
                "start_time": local.strftime("%H:%M:%S"),
                "sport": normalize_sport(raw_type),
                "raw_type": raw_type,
                "name": _get(row, idx, "Activity Name"),
                "duration_s": moving or elapsed,
                "elapsed_s": elapsed,
                "distance_m": _num(_get(row, idx, "Distance")),
                "elevation_m": _num(_get(row, idx, "Elevation Gain")),
                "avg_hr": _num(_get(row, idx, "Average Heart Rate")),
                "max_hr": _num(_get(row, idx, "Max Heart Rate")),
                "avg_power": _num(_get(row, idx, "Average Watts")),
                "weighted_power": _num(_get(row, idx, "Weighted Average Power")),
                "avg_speed_mps": _num(_get(row, idx, "Average Speed")),
                "perceived_exertion": _num(_get(row, idx, "Perceived Exertion")),
                "strava_relative_effort": _num(_get(row, idx, "Relative Effort")),
            })
    return rows


def load_strava():
    d = find_dir(STRAVA_DIR_CANDIDATES, STRAVA_KEY_FILE)
    if d is None:
        return []
    print(f"   reading {d / STRAVA_KEY_FILE}")
    return parse_activities_csv(d / STRAVA_KEY_FILE)
