"""Weekly plan generator: periodization, volume progression and workout templates.

Everything tunable lives in the CONSTANTS block at the top. The flow is:

  1. Phase for a week = days from that Monday to race day (base/build/peak/taper/race).
  2. Volume progression = ramp <=10%/week from what you actually did, capped by
     the phase target, with a deload every 4th week.
  3. The upcoming week is then adjusted for last week's completion, recovery
     metrics (HRV / resting HR / sleep) and current form (TSB).
  4. Weekly hours are split across sports and poured into a day-by-day template.
"""
from datetime import date, timedelta

from .config import RACE_DATE
from .training_load import MAX_WEEKLY_RAMP, week_start

# ---------------------------------------------------------------- CONSTANTS --
PEAK_WEEK_HOURS = 11.0        # biggest week you want to hit (70.3 age-grouper)
MIN_WEEK_HOURS = 3.5          # never plan less than this outside race week
LONG_RUN_MAX_MIN = 135
LONG_BIKE_MAX_MIN = 210

# Phase by days-to-race measured from the week's Monday (checked in order).
PHASES = [
    (7, "race"),
    (21, "taper"),
    (49, "peak"),
    (105, "build"),
    (10 ** 6, "base"),
]
PHASE_TARGET_FRACTION = {"base": 0.70, "build": 0.90, "peak": 1.00, "taper": 0.55, "race": 0.30}
RECOVERY_EVERY_N_WEEKS = 4    # every 4th week is a deload
RECOVERY_WEEK_FACTOR = 0.65   # deload = 65% of the surrounding weeks
LOW_COMPLETION_THRESHOLD = 0.60   # below this, hold volume instead of ramping
CAUTION_FACTOR = 0.85         # applied when recovery metrics look poor
DEEP_FATIGUE_TSB = -25        # TSB below this -> ease off
DEEP_FATIGUE_FACTOR = 0.90

SPORT_SPLIT = {
    "base":  {"swim": 0.25, "bike": 0.35, "run": 0.30, "strength": 0.10},
    "build": {"swim": 0.20, "bike": 0.42, "run": 0.30, "strength": 0.08},
    "peak":  {"swim": 0.18, "bike": 0.47, "run": 0.30, "strength": 0.05},
    "taper": {"swim": 0.20, "bike": 0.45, "run": 0.30, "strength": 0.05},
    "race":  {"swim": 0.25, "bike": 0.40, "run": 0.35, "strength": 0.00},
}

# Weekly template: (weekday 0=Mon, sport, role, share of that sport's weekly minutes, priority)
# Lower priority number = dropped first when there aren't enough hours.
WEEK_TEMPLATE = [
    (0, "swim", "technique", 0.45, 3),
    (0, "strength", "strength", 1.0, 2),
    (1, "run", "quality", 0.30, 4),
    (2, "bike", "quality", 0.35, 4),
    (3, "swim", "endurance", 0.55, 5),
    (4, "run", "easy", 0.20, 1),
    (5, "bike", "long", 0.65, 6),
    (5, "run", "brick", 0.10, 2),
    (6, "run", "long", 0.40, 6),
]
BRICK_PHASES = {"build", "peak", "taper"}
MIN_SESSION_MIN = {"swim": 30, "bike": 45, "run": 30, "strength": 30}

SPORT_EMOJI = {"swim": "🏊", "bike": "🚴", "run": "🏃", "strength": "💪", "race": "🏁", "rest": "😴"}
# ------------------------------------------------------------ END CONSTANTS --


def phase_for(monday):
    days = (RACE_DATE - monday).days
    for limit, name in PHASES:
        if days <= limit:
            return name
    return "base"


def upcoming_monday(today):
    return today if today.weekday() == 0 else today + timedelta(days=7 - today.weekday())


def _zone_str(zones, sport, z):
    hz = zones.get(sport, {}).get("hr_zones")
    if not hz:
        return z
    zz = next((x for x in hz if x["zone"] == z), None)
    return f"{z} ({zz['low']}-{zz['high']} bpm)" if zz else z


def _pace_str(zones, z):
    pz = zones.get("run", {}).get("pace_zones")
    if not pz:
        return ""
    zz = next((x for x in pz if x["zone"] == z), None)
    return f", ~{zz['slow']}-{zz['fast']}/km" if zz else ""


def describe(sport, role, phase, minutes, zones, is_recovery):
    """Title, intensity label and main-set description for one session."""
    z = lambda s, zz: _zone_str(zones, s, zz)
    if is_recovery and role in ("quality", "brick"):
        role = "easy"

    if sport == "swim":
        if role == "technique":
            return ("Swim: technique + short intervals", "Z2-Z3 (RPE 4-6)",
                    f"WU 200 easy + 4x50 drill/swim. Main: 8-12x50 focus on catch & body position, "
                    f"15s rest. Then 4x100 steady, 20s rest. CD 100. ~{minutes} min total.")
        sets = {"base": "4x200 steady, 30s rest", "build": "3x400 at 70.3 effort, 45s rest",
                "peak": "2x800 at race effort, 60s rest", "taper": "6x100 at race pace, 20s rest",
                "race": "10x50 smooth with 4 pick-ups"}
        return ("Swim: endurance", "Z2 (RPE 4-5)",
                f"WU 300 easy. Main: {sets.get(phase, sets['base'])}. Practice sighting every 6-8 "
                f"strokes on one set. CD 200. ~{minutes} min.")

    if sport == "bike":
        if role == "long":
            return ("Long ride", z("bike", "Z2"),
                    f"Steady aerobic ride, mostly {z('bike', 'Z2')}. "
                    + ("Include 2x20 min at 70.3 race effort (Z3) in the second half. " if phase in ("peak", "taper") else "")
                    + "Practise race nutrition: 60-90 g carbs/hour, drink to thirst.")
        if role == "easy":
            return ("Easy spin", z("bike", "Z1"), "Flat, easy, high cadence (90+ rpm). Purely recovery.")
        sets = {
            "base": ("Cadence + tempo", z("bike", "Z3"), "WU 15 min. 3x10 min at low Z3, 90-95 rpm, 5 min easy between. CD 10 min."),
            "build": ("Sweet-spot intervals", z("bike", "Z3") + "-" + z("bike", "Z4"), "WU 15 min. 3x12 min at upper Z3 / low Z4, 5 min easy between. CD 10 min."),
            "peak": ("Threshold intervals", z("bike", "Z4"), "WU 15 min. 4x8 min at Z4, 4 min easy between. CD 10 min."),
            "taper": ("Race-pace openers", z("bike", "Z3"), "WU 15 min. 3x6 min at 70.3 race effort, 4 min easy. Short and sharp - stop feeling fresh."),
            "race": ("Openers", z("bike", "Z3"), "20 min easy with 3x1 min at race effort. Check bike, gears, tyres."),
        }
        return sets[phase]

    if sport == "run":
        if role == "long":
            return ("Long run", z("run", "Z2") + _pace_str(zones, "Z2"),
                    f"Easy, conversational. "
                    + ("Last 20 min at 70.3 race pace (Z3). " if phase in ("peak", "taper") else "")
                    + "Walk breaks are fine early in the plan. Fuel every 30-40 min.")
        if role == "brick":
            return ("Brick run (straight off the bike)", z("run", "Z2") + "-" + z("run", "Z3"),
                    "Transition in under 5 min, then run steady. First 10 min at race pace, settle into Z2. Practise legs-off-bike feeling.")
        if role == "easy":
            return ("Easy run", z("run", "Z1") + "-" + z("run", "Z2") + _pace_str(zones, "Z2"),
                    "Recovery jog. Keep it genuinely easy - if in doubt, slow down. Optional 4x20s strides at the end.")
        sets = {
            "base": ("Tempo run", z("run", "Z3") + _pace_str(zones, "Z3"), "WU 15 min easy. 2x10 min at Z3 with 3 min jog between. CD 10 min. Add 4x20s strides."),
            "build": ("Threshold intervals", z("run", "Z4") + _pace_str(zones, "Z4"), "WU 15 min. 5x5 min at Z4, 2 min jog between. CD 10 min."),
            "peak": ("Race-pace run", z("run", "Z3") + _pace_str(zones, "Z3"), "WU 15 min. 3x12 min at 70.3 race pace (upper Z3), 3 min jog. CD 10 min."),
            "taper": ("Sharpener", z("run", "Z3") + _pace_str(zones, "Z3"), "WU 15 min. 4x4 min at race pace, 2 min jog. CD 10 min. Stop while it feels easy."),
            "race": ("Shakeout", z("run", "Z1"), "15-20 min easy with 4x20s strides. Lay out race kit afterwards."),
        }
        return sets[phase]

    if sport == "strength":
        core = "Core (planks, dead bugs, bird dogs) 10 min. "
        if phase in ("taper", "race"):
            return ("Strength: maintenance", "Light", core + "Bodyweight only: squats, lunges, glute bridges 2x12. No soreness allowed.")
        return ("Strength + mobility", "Moderate",
                core + "Squats, RDLs, step-ups, single-leg calf raises 3x8-10. Hip mobility 10 min. Finish with 5 min stretching.")

    return ("Session", "Easy", "")


def _allocate(target_hours, phase, is_recovery):
    """Turn weekly hours into a list of sessions with minutes, honouring
    per-session minimums and dropping low-priority sessions if hours are tight."""
    split = SPORT_SPLIT[phase]
    sport_minutes = {s: target_hours * 60 * f for s, f in split.items()}
    template = [t for t in WEEK_TEMPLATE if not (t[2] == "brick" and (phase not in BRICK_PHASES or is_recovery))]
    if is_recovery:
        template = [t for t in template if t[2] != "easy"]
    if phase == "race":
        template = [t for t in template if t[1] != "strength"]

    while True:
        sessions = []
        for weekday, sport, role, share, prio in template:
            total_share = sum(t[3] for t in template if t[1] == sport)
            minutes = sport_minutes.get(sport, 0) * (share / total_share) if total_share else 0
            sessions.append({"weekday": weekday, "sport": sport, "role": role,
                             "minutes": minutes, "prio": prio})
        # Drop the lowest-priority session that falls under 70% of its minimum.
        under = [s for s in sessions if s["minutes"] < 0.7 * MIN_SESSION_MIN[s["sport"]]]
        if not under:
            break
        victim = min(under, key=lambda s: s["prio"])
        template = [t for t in template if not (t[0] == victim["weekday"] and t[1] == victim["sport"] and t[2] == victim["role"])]
        if not template:
            break

    for s in sessions:
        s["minutes"] = max(MIN_SESSION_MIN[s["sport"]], s["minutes"])
        if s["role"] == "long" and s["sport"] == "run":
            s["minutes"] = min(s["minutes"], LONG_RUN_MAX_MIN)
        if s["role"] == "long" and s["sport"] == "bike":
            s["minutes"] = min(s["minutes"], LONG_BIKE_MAX_MIN)
        s["minutes"] = int(round(s["minutes"] / 5.0) * 5)
    return sessions


def _race_week_sessions():
    return [
        {"weekday": 0, "sport": "swim", "role": "endurance", "minutes": 30, "prio": 9},
        {"weekday": 1, "sport": "bike", "role": "quality", "minutes": 40, "prio": 9},
        {"weekday": 2, "sport": "run", "role": "quality", "minutes": 25, "prio": 9},
        {"weekday": 4, "sport": "swim", "role": "endurance", "minutes": 20, "prio": 9},
        {"weekday": 5, "sport": "bike", "role": "quality", "minutes": 20, "prio": 9},
    ]


def build_timeline(today, baseline_hours):
    """Project every week from the upcoming Monday to race day."""
    monday = upcoming_monday(today)
    level = max(MIN_WEEK_HOURS, baseline_hours)
    weeks, i = [], 0
    peak_level = level
    while monday < RACE_DATE:
        phase = phase_for(monday)
        is_recovery = phase in ("base", "build", "peak") and (i + 1) % RECOVERY_EVERY_N_WEEKS == 0
        if phase in ("taper", "race"):
            target = peak_level * PHASE_TARGET_FRACTION[phase]
        else:
            cap = PEAK_WEEK_HOURS * PHASE_TARGET_FRACTION[phase]
            level = min(level * (1 + MAX_WEEKLY_RAMP), max(cap, MIN_WEEK_HOURS))
            peak_level = max(peak_level, level)
            target = level * RECOVERY_WEEK_FACTOR if is_recovery else level
        weeks.append({
            "week_start": monday.isoformat(), "phase": phase, "is_recovery": is_recovery,
            "target_hours": round(target, 1), "weeks_to_race": (RACE_DATE - monday).days // 7,
        })
        monday += timedelta(days=7)
        i += 1
    return weeks


def evaluate_completion(plan, activities):
    """Match last week's planned sessions against actual activities."""
    if not plan:
        return None
    ws = date.fromisoformat(plan["week_start"])
    we = ws + timedelta(days=6)
    week_acts = [a for a in activities if ws.isoformat() <= a["date"] <= we.isoformat()]
    used = set()
    results = []
    for w in plan["workouts"]:
        if w["sport"] in ("rest", "race"):
            continue
        match = None
        for a in sorted(week_acts, key=lambda a: a["date"] != w["date"]):
            if a["id"] in used or a["sport"] != w["sport"]:
                continue
            if a["date"] != w["date"] and abs((date.fromisoformat(a["date"]) - date.fromisoformat(w["date"])).days) > 1:
                continue
            match = a
            break
        if match:
            used.add(match["id"])
        actual_min = (match["duration_s"] / 60) if match else 0
        results.append({**w, "completed": bool(match) and actual_min >= 0.6 * w["duration_min"],
                        "actual_min": round(actual_min), "actual_id": match["id"] if match else None})
    planned = [r for r in results]
    done = sum(1 for r in planned if r["completed"])
    planned_h = sum(r["duration_min"] for r in planned) / 60
    actual_h = sum((a["duration_s"] or 0) for a in week_acts) / 3600
    return {
        "week_start": plan["week_start"], "phase": plan["phase"], "is_recovery": plan.get("is_recovery", False),
        "planned_sessions": len(planned), "completed_sessions": done,
        "completion": round(done / len(planned), 2) if planned else None,
        "planned_hours": round(planned_h, 1), "actual_hours": round(actual_h, 1),
        "workouts": results,
    }


def generate_week(today, weekly, load, recovery_status, zones, last_week_eval):
    """Build the plan for the upcoming Monday-Sunday."""
    monday = upcoming_monday(today)
    phase = phase_for(monday)

    # The current week only counts as "last week" once it is (nearly) over;
    # running mid-week should look at the previous full week instead.
    cutoff = monday if today.weekday() >= 5 or today == monday else week_start(today)
    recent = [w for w in weekly if w["week_start"] < cutoff.isoformat()][-4:]
    last = recent[-1] if recent else None
    last_hours = last["total_hours"] if last else 0
    baseline = sum(w["total_hours"] for w in recent) / len(recent) if recent else MIN_WEEK_HOURS
    if last_week_eval and last_week_eval.get("is_recovery") and len(recent) >= 2:
        last_hours = max(last_hours, recent[-2]["total_hours"])

    timeline = build_timeline(today, max(baseline, last_hours))
    this = timeline[0]
    is_recovery = this["is_recovery"]
    reasons = []

    if phase in ("taper", "race"):
        target = this["target_hours"]
        reasons.append(f"{phase.capitalize()} phase: volume drops to {int(PHASE_TARGET_FRACTION[phase]*100)}% of your peak so you arrive fresh.")
    else:
        cap = PEAK_WEEK_HOURS * PHASE_TARGET_FRACTION[phase]
        ramp_base = max(last_hours, MIN_WEEK_HOURS)
        target = min(ramp_base * (1 + MAX_WEEKLY_RAMP), cap)
        reasons.append(f"{phase.capitalize()} phase (cap {cap:.1f} h/wk). Last week you did {last_hours:.1f} h, so this week ramps to at most +{int(MAX_WEEKLY_RAMP*100)}%.")
        if last_week_eval and last_week_eval.get("completion") is not None and last_week_eval["completion"] < LOW_COMPLETION_THRESHOLD:
            target = min(target, max(last_hours, MIN_WEEK_HOURS))
            reasons.append(f"Only {int(last_week_eval['completion']*100)}% of last week's sessions were completed, so volume is held rather than increased.")
        if is_recovery:
            target *= RECOVERY_WEEK_FACTOR
            reasons.append("Scheduled deload week: -35% volume, no hard intervals. Let the fitness soak in.")

    if recovery_status["flag"] == "caution":
        target *= CAUTION_FACTOR
        reasons.append("Recovery metrics flag caution (" + "; ".join(recovery_status["reasons"]) + "), so the week is 15% lighter.")
    elif recovery_status["flag"] == "good":
        reasons.append("Recovery metrics look good (" + "; ".join(recovery_status["reasons"]) + ").")

    tsb = load[-1]["tsb"] if load else 0
    if tsb < DEEP_FATIGUE_TSB and phase not in ("taper", "race"):
        target *= DEEP_FATIGUE_FACTOR
        reasons.append(f"Form (TSB) is {tsb:.0f}: you are carrying a lot of fatigue, so 10% is shaved off.")

    target = round(max(target, 1.5), 1)
    sessions = _race_week_sessions() if phase == "race" else _allocate(target, phase, is_recovery)

    workouts = []
    for s in sorted(sessions, key=lambda s: (s["weekday"], s["prio"] * -1)):
        d = monday + timedelta(days=s["weekday"])
        title, intensity, desc = describe(s["sport"], s["role"], phase, s["minutes"], zones, is_recovery)
        workouts.append({
            "date": d.isoformat(), "weekday": d.strftime("%A"), "sport": s["sport"], "role": s["role"],
            "title": title, "duration_min": s["minutes"], "intensity": intensity, "description": desc,
            "emoji": SPORT_EMOJI[s["sport"]],
        })
    scheduled_days = {w["date"] for w in workouts}
    for i in range(7):
        d = monday + timedelta(days=i)
        if d.isoformat() not in scheduled_days and d < RACE_DATE:
            workouts.append({"date": d.isoformat(), "weekday": d.strftime("%A"), "sport": "rest", "role": "rest",
                             "title": "Rest day", "duration_min": 0, "intensity": "-",
                             "description": "Full rest or 20 min gentle walk / mobility.", "emoji": SPORT_EMOJI["rest"]})
    if monday <= RACE_DATE <= monday + timedelta(days=7):
        workouts.append({"date": RACE_DATE.isoformat(), "weekday": RACE_DATE.strftime("%A"), "sport": "race", "role": "race",
                         "title": "RACE DAY - Half Ironman 70.3", "duration_min": 330, "intensity": "Race",
                         "description": "1.9 km swim / 90 km bike / 21.1 km run. Swim smooth, bike controlled (Z3, never Z4), "
                                        "run the first 5 km slower than feels right. Eat 60-90 g carbs/h on the bike.",
                         "emoji": SPORT_EMOJI["race"]})
    workouts.sort(key=lambda w: (w["date"], w["sport"] == "strength", w["sport"] == "run" and w["role"] == "brick"))

    focus = {
        "base": "Build aerobic base and swim consistency; keep intensity low and frequency high.",
        "build": "Introduce threshold work on the bike and run; long ride grows with a brick run after it.",
        "peak": "Race-specific: long sessions at 70.3 effort, bricks every weekend, nail nutrition.",
        "taper": "Keep intensity, cut volume. Sleep, hydrate, trust the work.",
        "race": "Stay sharp and calm. Short openers only. Race day is coming.",
    }[phase]
    return {
        "week_start": monday.isoformat(), "week_end": (monday + timedelta(days=6)).isoformat(),
        "phase": phase, "is_recovery": is_recovery, "weeks_to_race": this["weeks_to_race"],
        "target_hours": target, "planned_hours": round(sum(w["duration_min"] for w in workouts if w["sport"] != "race") / 60, 1),
        "focus": focus, "reasons": reasons, "workouts": workouts, "timeline": timeline,
    }
