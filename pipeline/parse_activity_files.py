"""Parse raw activity files (.fit, .gpx, .tcx, optionally .gz) from a Strava
export's activities/ folder into the same rows parse_strava produces.

This is the fallback for when activities.csv is missing or older than the files
next to it. Rows get source_id "file:<file name>"; when a later activities.csv
lists that file, db.upsert_activities swaps the file row for the CSV row (the
CSV has Strava's moving time, name and relative effort).

Standard library only: the FIT reader decodes just the session summary message.
"""
import gzip
import math
import struct
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from .parse_strava import normalize_sport

SUFFIXES = (".fit", ".fit.gz", ".gpx", ".gpx.gz", ".tcx", ".tcx.gz")

# FIT sport enum -> Strava-style activity type (normalize_sport maps it on).
FIT_SPORTS = {1: "Run", 2: "Ride", 5: "Swim", 4: "Workout", 10: "WeightTraining", 11: "Walk", 17: "Hike"}
# GPX <type> / TCX Sport values -> Strava-style activity type.
TEXT_SPORTS = {
    "running": "Run", "run": "Run", "trail_running": "TrailRun", "9": "Run",
    "cycling": "Ride", "biking": "Ride", "ride": "Ride", "1": "Ride",
    "mountain_biking": "MountainBikeRide", "road_biking": "Ride", "gravel_cycling": "GravelRide",
    "swimming": "Swim", "swim": "Swim", "open_water_swimming": "OpenWaterSwim", "lap_swimming": "Swim",
    "walking": "Walk", "hiking": "Hike", "training": "Workout", "strength_training": "WeightTraining",
}

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=timezone.utc)
MOVING_GAP_S = 30        # a gap between track points longer than this is a stop
MOVING_MIN_SPEED = 0.5   # m/s; slower than this between points counts as stopped
ELEV_NOISE_M = 2.0       # ignore GPS altitude wiggles smaller than this


def is_activity_file(path):
    return path.is_file() and path.name.lower().endswith(SUFFIXES)


def _read(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.name.lower().endswith(".gz") else data


def _row(path, start_utc, raw_type, name, moving_s, elapsed_s, distance_m, elevation_m=None,
         avg_hr=None, max_hr=None, avg_power=None, weighted_power=None, avg_speed=None):
    local = start_utc.astimezone()
    if not avg_speed and distance_m and moving_s:
        avg_speed = distance_m / moving_s
    return {
        "source_id": f"file:{path.name}",
        "date": local.date().isoformat(),
        "start_time": local.strftime("%H:%M:%S"),
        "sport": normalize_sport(raw_type),
        "raw_type": raw_type,
        "name": name or f"{raw_type} (from file)",
        "duration_s": moving_s or elapsed_s,
        "elapsed_s": elapsed_s,
        "distance_m": distance_m,
        "elevation_m": elevation_m,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "avg_power": avg_power,
        "weighted_power": weighted_power,
        "avg_speed_mps": avg_speed,
        "perceived_exertion": None,
        "strava_relative_effort": None,
    }


# --- FIT ---------------------------------------------------------------------

def _fit_messages(data, wanted):
    """Yield (global_num, {field_number: raw_value}) for data messages whose global
    number is in `wanted`. Compressed-timestamp records get field 253 filled in."""
    header_size = data[0]
    end = header_size + struct.unpack("<I", data[4:8])[0]
    defs, i, last_ts = {}, header_size, None
    while i < end:
        h = data[i]
        i += 1
        ts = None
        if h & 0x80:                      # compressed-timestamp data record
            local = (h >> 5) & 0x3
            if last_ts is not None:
                ts = (last_ts & ~0x1F) + (h & 0x1F)
                if ts < last_ts:
                    ts += 0x20
        elif h & 0x40:                    # definition record
            local = h & 0xF
            arch = "<" if data[i + 1] == 0 else ">"
            global_num = struct.unpack(arch + "H", data[i + 2:i + 4])[0]
            n = data[i + 4]
            i += 5
            fields = [(data[i + 3 * k], data[i + 3 * k + 1]) for k in range(n)]
            i += 3 * n
            dev_size = 0
            if h & 0x20:                  # developer fields
                m = data[i]
                i += 1
                dev_size = sum(data[i + 3 * k + 1] for k in range(m))
                i += 3 * m
            defs[local] = (global_num, arch, fields, dev_size)
            continue
        else:
            local = h & 0xF
        global_num, arch, fields, dev_size = defs[local]
        rec = {}
        for num, size in fields:
            raw = data[i:i + size]
            i += size
            fmt = {1: "B", 2: "H", 4: "I"}.get(size)
            if fmt and (global_num in wanted or num == 253):
                v = struct.unpack(arch + fmt, raw)[0]
                if v != (1 << (8 * size)) - 1:   # all bits set = invalid
                    rec[num] = v
        i += dev_size
        if ts is not None:
            rec.setdefault(253, ts)
        if 253 in rec:
            last_ts = rec[253]
        if global_num in wanted:
            yield global_num, rec


def _fit_session(data):
    """Return {field_number: raw_value} of the first session message (global 18)."""
    return next((rec for _, rec in _fit_messages(data, {18})), None)


def _fit_hr_stream(data):
    """[(seconds, bpm)] from record messages (global 20: 253 timestamp, 3 heart_rate)."""
    return [(rec[253], rec[3]) for _, rec in _fit_messages(data, {20}) if 253 in rec and 3 in rec]


def parse_fit(path):
    s = _fit_session(_read(path))
    if not s or 2 not in s:
        return None
    raw_type = FIT_SPORTS.get(s.get(5), "Workout")
    if raw_type == "Workout" and s.get(6) == 20:      # training / strength_training
        raw_type = "WeightTraining"
    ms = lambda k: s[k] / 1000 if k in s else None
    speed = s.get(124, s.get(14))                      # enhanced_avg_speed, avg_speed (mm/s)
    return _row(
        path, FIT_EPOCH + timedelta(seconds=s[2]), raw_type, None,
        moving_s=ms(8), elapsed_s=ms(7),
        distance_m=s[9] / 100 if 9 in s else None,
        elevation_m=s.get(22), avg_hr=s.get(16), max_hr=s.get(17),
        avg_power=s.get(20), weighted_power=s.get(34),
        avg_speed=speed / 1000 if speed else None,
    )


# --- GPX / TCX -----------------------------------------------------------------

def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _time(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))


def _haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def _track_stats(points):
    """points: [(time, (lat, lon) or None, ele or None, hr or None)] in order."""
    times = [p[0] for p in points]
    elapsed = (times[-1] - times[0]).total_seconds()
    dist = moving = gain = 0.0
    last_ele = None
    for prev, cur in zip(points, points[1:]):
        dt = (cur[0] - prev[0]).total_seconds()
        d = _haversine(prev[1], cur[1]) if prev[1] and cur[1] else 0.0
        dist += d
        if 0 < dt <= MOVING_GAP_S and d / dt >= MOVING_MIN_SPEED:
            moving += dt
    for p in points:
        if p[2] is None:
            continue
        if last_ele is None or abs(p[2] - last_ele) >= ELEV_NOISE_M:
            if last_ele is not None and p[2] > last_ele:
                gain += p[2] - last_ele
            last_ele = p[2]
    hrs = [p[3] for p in points if p[3]]
    return {
        "elapsed": elapsed, "moving": moving or None, "distance": dist or None, "gain": gain or None,
        "avg_hr": round(sum(hrs) / len(hrs), 1) if hrs else None, "max_hr": max(hrs) if hrs else None,
    }


def parse_gpx(path):
    root = ET.fromstring(_read(path))
    name = raw = None
    points = []
    for el in root.iter():
        tag = _local(el.tag)
        if tag == "trk":
            for child in el:
                if _local(child.tag) == "name" and child.text:
                    name = child.text.strip()
                elif _local(child.tag) == "type" and child.text:
                    raw = child.text.strip().lower()
        elif tag == "trkpt":
            t = ele = hr = None
            for c in el.iter():
                ct = _local(c.tag)
                if ct == "time" and c.text:
                    t = _time(c.text)
                elif ct == "ele" and c.text:
                    ele = float(c.text)
                elif ct == "hr" and c.text:
                    hr = float(c.text)
            if t:
                points.append((t, (float(el.get("lat")), float(el.get("lon"))), ele, hr))
    if len(points) < 2:
        return None
    st = _track_stats(points)
    return _row(path, points[0][0], TEXT_SPORTS.get(raw, "Workout"), name, st["moving"], st["elapsed"],
                st["distance"], st["gain"], st["avg_hr"], st["max_hr"])


def parse_tcx(path):
    root = ET.fromstring(_read(path))
    act = next((e for e in root.iter() if _local(e.tag) == "Activity"), None)
    if act is None:
        return None
    raw = TEXT_SPORTS.get((act.get("Sport") or "").lower(), "Workout")
    points, timer, dist = [], 0.0, 0.0
    for el in act.iter():
        tag = _local(el.tag)
        if tag == "Lap":
            for c in el:
                if _local(c.tag) == "TotalTimeSeconds" and c.text:
                    timer += float(c.text)
                elif _local(c.tag) == "DistanceMeters" and c.text:
                    dist += float(c.text)
        elif tag == "Trackpoint":
            t = pos = ele = hr = None
            lat = lon = None
            for c in el.iter():
                ct = _local(c.tag)
                if ct == "Time" and c.text:
                    t = _time(c.text)
                elif ct == "LatitudeDegrees":
                    lat = float(c.text)
                elif ct == "LongitudeDegrees":
                    lon = float(c.text)
                elif ct == "AltitudeMeters" and c.text:
                    ele = float(c.text)
                elif ct == "Value" and c.text:    # HeartRateBpm/Value
                    hr = float(c.text)
            if lat is not None and lon is not None:
                pos = (lat, lon)
            if t:
                points.append((t, pos, ele, hr))
    if not points:
        return None
    st = _track_stats(points) if len(points) > 1 else {"elapsed": timer, "moving": None, "distance": None,
                                                        "gain": None, "avg_hr": None, "max_hr": None}
    return _row(path, points[0][0], raw, None, timer or st["moving"], st["elapsed"],
                dist or st["distance"], st["gain"], st["avg_hr"], st["max_hr"])


def parse_activity_file(path):
    """Return one activity row, or None if the file has no usable data."""
    n = path.name.lower()
    try:
        if ".fit" in n:
            return parse_fit(path)
        if ".gpx" in n:
            return parse_gpx(path)
        if ".tcx" in n:
            return parse_tcx(path)
    except Exception as e:  # one corrupt file should not stop the weekly run
        print(f"   ! could not read {path.name}: {e}")
    return None


# --- Heart-rate streams -----------------------------------------------------------

HR_GAP_S = 30               # a gap longer than this breaks a window (a stop lets HR fall)
HR_PLAUSIBLE = (35, 230)    # samples outside this are sensor dropouts or spikes


def _text_hr_stream(root):
    """[(seconds, bpm)] from GPX trkpt/hr or TCX Trackpoint/HeartRateBpm/Value."""
    out = []
    for el in root.iter():
        if _local(el.tag) not in ("trkpt", "Trackpoint"):
            continue
        t = hr = None
        for c in el.iter():
            ct = _local(c.tag)
            if ct in ("time", "Time") and c.text:
                t = _time(c.text)
            elif ct in ("hr", "Value") and c.text:
                hr = float(c.text)
        if t and hr:
            out.append((t.timestamp(), hr))
    return out


def hr_stream(path):
    """Per-sample heart rate [(seconds, bpm)] from a raw activity file, or [] if it has none."""
    n = path.name.lower()
    try:
        data = _read(path)
        s = _fit_hr_stream(data) if ".fit" in n else _text_hr_stream(ET.fromstring(data))
    except Exception as e:
        print(f"   ! could not read HR from {path.name}: {e}")
        return []
    return [(t, hr) for t, hr in s if HR_PLAUSIBLE[0] <= hr <= HR_PLAUSIBLE[1]]


def best_hr_window(samples, secs):
    """Highest mean HR over any unbroken `secs`-second stretch (samples held until the
    next one, resampled to 1 Hz). None if no stretch is that long."""
    series = []
    for (t1, h1), (t2, _) in zip(samples, samples[1:]):
        dt = int(t2 - t1)
        if dt <= 0:
            continue
        series.extend([None] if dt > HR_GAP_S else [h1] * dt)
    best, total, run = None, 0.0, 0
    for i, v in enumerate(series):
        if v is None:
            total, run = 0.0, 0
            continue
        total += v
        run += 1
        if run > secs:
            total -= series[i - secs]
            run -= 1
        if run == secs and (best is None or total > best * secs):
            best = total / secs
    return round(best, 1) if best is not None else None
