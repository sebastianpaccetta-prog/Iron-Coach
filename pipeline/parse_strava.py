"""Parse a Strava bulk export into normalized activity rows.

activities.csv is the main source: it already carries everything the plan needs
(moving time, distance, HR, power, elevation, RPE). The raw .fit/.gpx/.tcx files
in the export's activities/ folder are the fallback for anything the CSV does not
cover - no CSV at all, or files newer than the CSV (see parse_activity_files).
The ~40 social/profile CSVs in the export are ignored.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

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
                "filename": Path(_get(row, idx, "Filename") or "").name or None,
            })
    return rows


def activity_files(candidates=None):
    """Raw activity files in any export location: <dir>/activities/, one folder
    deeper (<dir>/<export>/activities/), or loose in <dir>. Deduplicated by name."""
    from .parse_activity_files import is_activity_file
    found = {}
    for c in candidates or STRAVA_DIR_CANDIDATES:
        if not c.is_dir():
            continue
        for folder in [c, c / "activities", *c.glob("*/activities")]:
            if folder.is_dir():
                for f in folder.iterdir():
                    if is_activity_file(f):
                        found.setdefault(f.name, f)
    return sorted(found.values(), key=lambda f: f.name)


def best_hr_efforts(pending, strava_rows, window_s=1200):
    """{activity id: highest `window_s` mean HR or None} for `pending` db rows, read
    from their raw files. CSV rows are matched to files through the CSV's Filename
    column; rows imported from a file carry the name in their source id. Rows whose
    file is named but not on disk are left out, so a later export can fill them in."""
    from .parse_activity_files import best_hr_window, hr_stream
    files = {f.name: f for f in activity_files()}
    by_key = {(r["date"], r["start_time"], r["sport"]): r["filename"] for r in strava_rows if r.get("filename")}
    out = {}
    for a in pending:
        sid = a["source_id"] or ""
        name = sid[5:] if sid.startswith("file:") else by_key.get((a["date"], a["start_time"], a["sport"]))
        path = files.get(name)
        if name and not path:
            continue
        out[a["id"]] = best_hr_window(hr_stream(path), window_s) if path else None
    return out


def load_strava(known_source_ids=(), imported_until=None):
    """Rows from the newest activities.csv, plus rows parsed from raw activity
    files that the CSV does not list and that start after its newest activity
    (or after `imported_until`, the newest CSV-imported (date, start_time) already
    in the database, whichever is later). Files whose "file:<name>" source id is
    in known_source_ids were imported on an earlier run and are not re-parsed."""
    from .parse_activity_files import parse_activity_file
    rows = []
    d = find_dir(STRAVA_DIR_CANDIDATES, STRAVA_KEY_FILE)
    if d is not None:
        print(f"   reading {d / STRAVA_KEY_FILE}")
        rows = parse_activities_csv(d / STRAVA_KEY_FILE)
    else:
        print(f"   no {STRAVA_KEY_FILE} found - reading the raw activity files instead")
    listed = {r["filename"] for r in rows if r.get("filename")}
    csv_newest = max([(r["date"], r["start_time"]) for r in rows] + ([tuple(imported_until)] if imported_until else []),
                     default=None)

    extra, skipped_old = [], 0
    for f in activity_files():
        if f.name in listed or f"file:{f.name}" in known_source_ids:
            continue
        r = parse_activity_file(f)
        if r is None:
            continue
        # A file older than the CSV's newest activity but missing from it was
        # deleted or merged on Strava (or is already in the db from an earlier
        # CSV); the CSV is the authority for that period.
        if csv_newest and (r["date"], r["start_time"]) <= csv_newest:
            skipped_old += 1
            continue
        extra.append(r)
    if extra:
        print(f"   {len(extra)} activities read from raw files"
              + (f" (newer than {STRAVA_KEY_FILE})" if rows else ""))
    if skipped_old:
        print(f"   {skipped_old} raw files skipped: already imported or covered by {STRAVA_KEY_FILE}")
    return rows + extra
