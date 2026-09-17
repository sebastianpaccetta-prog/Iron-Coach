"""Stream-parse Apple Health export.xml for recovery metrics only.

The export can be several GB, so we never build a DOM. Apple writes one
<Record .../> per line, so we scan line by line and only regex-parse lines whose
type is one of the four metrics we care about. Workout elements and everything
else (steps, clinical records, routes) are skipped entirely.
"""
import re
from collections import defaultdict
from datetime import datetime, timedelta

from .config import APPLE_HEALTH_DIR_CANDIDATES, APPLE_HEALTH_KEY_FILE, find_dir

TYPES = {
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv",
    "HKQuantityTypeIdentifierVO2Max": "vo2max",
    "HKCategoryTypeIdentifierSleepAnalysis": "sleep_hours",
}
ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
}

_ATTR = re.compile(r'(\w+)="([^"]*)"')
_TYPE_HINT = re.compile(r'type="(HK\w+)"')


def _parse_dt(s):
    # "2026-09-14 07:12:03 -0500"
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")


def parse_export(path, since=None):
    """Yield (date_iso, metric, value). Sleep is summed per night and attributed
    to the wake-up date; when several devices log the same night the largest
    total wins (avoids double counting phone + watch)."""
    quantity = defaultdict(list)        # (date, metric) -> [values]
    sleep = defaultdict(float)          # (date, source) -> hours

    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "<Record " not in line:
                continue
            m = _TYPE_HINT.search(line)
            if not m or m.group(1) not in TYPES:
                continue
            attrs = dict(_ATTR.findall(line))
            metric = TYPES[attrs.get("type", "")]
            try:
                start = _parse_dt(attrs["startDate"])
                end = _parse_dt(attrs["endDate"])
            except (KeyError, ValueError):
                continue
            if since and end.date() < since:
                continue

            if metric == "sleep_hours":
                if attrs.get("value") not in ASLEEP_VALUES:
                    continue
                hours = (end - start).total_seconds() / 3600
                # Attribute to wake date; sessions ending before 3pm belong to that morning.
                wake = end.date() if end.hour < 15 else (end + timedelta(days=1)).date()
                sleep[(wake.isoformat(), attrs.get("sourceName", ""))] += hours
            else:
                try:
                    v = float(attrs.get("value", ""))
                except ValueError:
                    continue
                quantity[(start.date().isoformat(), metric)].append(v)

    for (d, metric), vals in quantity.items():
        yield d, metric, sum(vals) / len(vals)

    best = defaultdict(float)
    for (d, _src), hours in sleep.items():
        best[d] = max(best[d], hours)
    for d, hours in best.items():
        if 0 < hours < 16:
            yield d, "sleep_hours", round(hours, 2)


def load_apple_health(since=None):
    d = find_dir(APPLE_HEALTH_DIR_CANDIDATES, APPLE_HEALTH_KEY_FILE)
    if d is None:
        return []
    print(f"   reading {d / APPLE_HEALTH_KEY_FILE}")
    return list(parse_export(d / APPLE_HEALTH_KEY_FILE, since=since))
