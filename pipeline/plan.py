"""Weekly plan generator: periodization, volume progression and workout templates.

Everything tunable lives in the CONSTANTS block at the top. The flow is:

  1. Phase for a week = days from that Monday to race day (base/build/peak/taper/race).
  2. Peak week hours are picked inside PEAK_WEEK_HOURS_RANGE from current fitness
     (recent weekly hours and CTL); volume ramps <=10%/week from what you
     actually did, capped by the phase target, with a deload every 4th week.
  3. The upcoming week is then adjusted for last week's completion, recovery
     metrics (HRV / resting HR / sleep) and current form (TSB). The long run is
     capped at 110% of your longest run in the last 30 days.
  4. Weekly hours are split across sports and poured into a day-by-day template.
     Race-pace targets in every session come from GOAL_TIME_H in config.py.

References for each rule are in SCIENCE.md.
"""
from datetime import date, timedelta

from .config import DIST_LABEL, GOAL_TIME_H, PEAK_WEEK_HOURS_RANGE, RACE_DATE, SPEED_LABEL, UNITS, goal_splits
from .training_load import MAX_LONG_RUN_SPIKE, MAX_WEEKLY_RAMP, longest_recent_run_min, week_start

# ---------------------------------------------------------------- CONSTANTS --
MIN_WEEK_HOURS = 3.5          # never plan less than this outside race week
LONG_RUN_MAX_MIN = 135
LONG_BIKE_MAX_MIN = 210
# Fitness -> peak week mapping. Baseline weekly hours between these bounds map
# linearly onto PEAK_WEEK_HOURS_RANGE; same for CTL. The two estimates are averaged.
PEAK_FROM_HOURS = (6.0, 10.0)   # <=6 h/wk now -> 11 h peak, >=10 h/wk -> 14 h
PEAK_FROM_CTL = (45.0, 80.0)    # CTL 45 -> 11 h, CTL 80 -> 14 h

# Phase by days-to-race measured from the week's Monday (checked in order).
# Taper is 2 weeks (taper + race week): the 2023 meta-analysis found 8-14 day
# tapers with 41-60% volume cut and intensity kept give the best time-trial gains.
PHASES = [
    (7, "race"),
    (14, "taper"),
    (49, "peak"),
    (105, "build"),
    (10 ** 6, "base"),
]
PHASE_TARGET_FRACTION = {"base": 0.70, "build": 0.90, "peak": 1.00, "taper": 0.55, "race": 0.40}
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

GOAL = goal_splits(GOAL_TIME_H)


def _fmt_mmss(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


# Race-pace strings used in session descriptions, derived from the goal time.
RACE_PACE = {
    "swim": f"{_fmt_mmss(GOAL['swim_s_per_100m'])}/100m",
    "bike": f"{GOAL['bike_speed']} {SPEED_LABEL}",
    "run": f"{_fmt_mmss(GOAL['run_s_per_dist'])}/{DIST_LABEL}",
}


def _lerp(x, x_range, y_range):
    lo, hi = x_range
    t = max(0.0, min(1.0, (x - lo) / (hi - lo)))
    return y_range[0] + t * (y_range[1] - y_range[0])


def peak_week_hours(baseline_hours, ctl=None):
    """Pick the biggest week inside PEAK_WEEK_HOURS_RANGE from current fitness.
    Recent weekly hours say what you can absorb; CTL says how much load you are
    already carrying. Both map linearly onto the range and are averaged."""
    est = [_lerp(baseline_hours, PEAK_FROM_HOURS, PEAK_WEEK_HOURS_RANGE)]
    if ctl:
        est.append(_lerp(ctl, PEAK_FROM_CTL, PEAK_WEEK_HOURS_RANGE))
    return round(sum(est) / len(est) * 2) / 2   # nearest 0.5 h


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
    return f", ~{zz['slow']}-{zz['fast']}/{DIST_LABEL}" if zz else ""


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
        rp = RACE_PACE["swim"]
        sets = {"base": "4x200 steady, 30s rest", "build": f"3x400 at race pace ({rp}), 45s rest",
                "peak": f"2x800 at race pace ({rp}), 60s rest", "taper": f"6x100 at race pace ({rp}), 20s rest",
                "race": "10x50 smooth with 4 pick-ups"}
        return ("Swim: endurance", "Z2 (RPE 4-5)",
                f"WU 300 easy. Main: {sets.get(phase, sets['base'])}. Practice sighting every 6-8 "
                f"strokes on one set. CD 200. ~{minutes} min.")

    if sport == "bike":
        rp = RACE_PACE["bike"]
        if role == "long":
            return ("Long ride", z("bike", "Z2"),
                    f"Steady aerobic ride, mostly {z('bike', 'Z2')}. "
                    + (f"Include 2x20 min at race effort (~{rp} on flat, Z3) in the second half. " if phase in ("peak", "taper") else "")
                    + "Fuel 90 g carbs/h (2:1 glucose:fructose); on long rides in build/peak practise up to 120 g/h to train the gut. Drink to thirst.")
        if role == "easy":
            return ("Easy spin", z("bike", "Z1"), "Flat, easy, high cadence (90+ rpm). Purely recovery.")
        sets = {
            "base": ("Cadence + tempo", z("bike", "Z3"), "WU 15 min. 3x10 min at low Z3, 90-95 rpm, 5 min easy between. CD 10 min."),
            "build": ("Sweet-spot intervals", z("bike", "Z3") + "-" + z("bike", "Z4"), "WU 15 min. 3x12 min at upper Z3 / low Z4, 5 min easy between. CD 10 min."),
            "peak": ("Threshold + VO2 intervals", z("bike", "Z4") + "-Z5", "WU 15 min. 3x8 min at Z4, 4 min easy, then 4x2 min at Z5, 2 min easy. CD 10 min."),
            "taper": ("Race-pace openers", z("bike", "Z3"), f"WU 15 min. 3x6 min at race effort (~{rp}), 4 min easy. Short and sharp - stop feeling fresh."),
            "race": ("Openers", z("bike", "Z3"), "20 min easy with 3x1 min at race effort. Check bike, gears, tyres."),
        }
        return sets[phase]

    if sport == "run":
        rp = RACE_PACE["run"]
        if role == "long":
            return ("Long run", z("run", "Z2") + _pace_str(zones, "Z2"),
                    f"Easy, conversational. "
                    + (f"Last 20 min at race pace ({rp}). " if phase in ("peak", "taper") else "")
                    + "Walk breaks are fine early in the plan. Fuel every 30-40 min.")
        if role == "brick":
            return ("Brick run (straight off the bike)", z("run", "Z2") + "-" + z("run", "Z3"),
                    f"Transition in under 5 min, then run steady. First 10 min at race pace ({rp}), settle into Z2. Practise legs-off-bike feeling.")
        if role == "easy":
            return ("Easy run", z("run", "Z1") + "-" + z("run", "Z2") + _pace_str(zones, "Z2"),
                    "Recovery jog. Keep it genuinely easy - if in doubt, slow down. Optional 4x20s strides at the end.")
        sets = {
            "base": ("Tempo run", z("run", "Z3") + _pace_str(zones, "Z3"), "WU 15 min easy. 2x10 min at Z3 with 3 min jog between. CD 10 min. Add 4x20s strides."),
            "build": ("Threshold intervals", z("run", "Z4") + _pace_str(zones, "Z4"), "WU 15 min. 5x5 min at Z4, 2 min jog between. CD 10 min."),
            "peak": ("Race-pace + VO2 run", z("run", "Z3") + "-Z5", f"WU 15 min. 3x10 min at race pace ({rp}), 3 min jog, then 5x1 min hard (Z5), 1 min jog. CD 10 min."),
            "taper": ("Sharpener", z("run", "Z3") + _pace_str(zones, "Z3"), f"WU 15 min. 4x4 min at race pace ({rp}), 2 min jog. CD 10 min. Stop while it feels easy."),
            "race": ("Shakeout", z("run", "Z1"), "15-20 min easy with 4x20s strides. Lay out race kit afterwards."),
        }
        return sets[phase]

    if sport == "strength":
        core = "Core (planks, dead bugs, bird dogs) 10 min. "
        if phase in ("taper", "race"):
            return ("Strength: maintenance", "Light", core + "Bodyweight only: squats, lunges, glute bridges 2x12. No soreness allowed.")
        # Heavy (>80% 1RM) loading + plyometrics improves running economy more than
        # moderate circuits (Llanos-Lagos 2024 meta-analysis).
        return ("Strength: heavy + plyo", "Heavy",
                core + "Squats or trap-bar deadlift 4x4-6 heavy (>80% 1RM, 3 min rest), RDLs 3x6, single-leg calf raises 3x10. "
                       "Then 3x8 pogo hops + 3x5 drop jumps. Hip mobility 10 min.")

    return ("Session", "Easy", "")


def _allocate(target_hours, phase, is_recovery, long_run_cap=None):
    """Turn weekly hours into a list of sessions with minutes, honouring
    per-session minimums and dropping low-priority sessions if hours are tight.
    `long_run_cap` (minutes) limits the long run to avoid a single-session spike."""
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
            if long_run_cap:
                s["minutes"] = min(s["minutes"], max(long_run_cap, MIN_SESSION_MIN["run"]))
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


def build_timeline(today, baseline_hours, peak_hours):
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
            cap = peak_hours * PHASE_TARGET_FRACTION[phase]
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


def _goal_check(zones):
    """Compare goal run pace with current threshold pace. A 70.3 run is held at
    roughly 88-92% of threshold speed, so the goal is realistic when goal pace
    is no faster than ~92% of threshold speed."""
    thr = zones.get("run", {}).get("threshold_pace")
    if not thr:
        return None
    m, s = thr.split(":")
    thr_s = int(m) * 60 + int(s)
    goal_s = GOAL["run_s_per_dist"]
    ratio = thr_s / goal_s   # goal speed as a fraction of threshold speed
    msg = (f"Goal {GOAL_TIME_H:.2f} h needs ~{RACE_PACE['run']} off the bike; "
           f"that is {ratio * 100:.0f}% of your current threshold speed ({thr}/{DIST_LABEL})")
    if ratio > 0.92:
        return msg + " - threshold needs to come down before this is realistic."
    return msg + " - within the sustainable 88-92% band."


def generate_week(today, weekly, load, recovery_status, zones, last_week_eval, activities=None):
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

    ctl = load[-1]["ctl"] if load else None
    peak_hours = peak_week_hours(baseline, ctl)
    timeline = build_timeline(today, max(baseline, last_hours), peak_hours)
    this = timeline[0]
    is_recovery = this["is_recovery"]
    reasons = [f"Peak week set to {peak_hours:.1f} h (range {PEAK_WEEK_HOURS_RANGE[0]:.0f}-{PEAK_WEEK_HOURS_RANGE[1]:.0f} h) "
               f"from your recent {baseline:.1f} h/wk and CTL {ctl:.0f}." if ctl is not None else
               f"Peak week set to {peak_hours:.1f} h from your recent {baseline:.1f} h/wk."]
    goal_msg = _goal_check(zones)
    if goal_msg:
        reasons.append(goal_msg)

    if phase in ("taper", "race"):
        target = this["target_hours"]
        reasons.append(f"{phase.capitalize()} phase: volume drops to {int(PHASE_TARGET_FRACTION[phase]*100)}% of your peak, intensity and frequency stay, so you arrive fresh.")
    else:
        cap = peak_hours * PHASE_TARGET_FRACTION[phase]
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

    # Single-session spike guard for the long run (Nielsen 2025).
    long_run_cap = None
    longest = longest_recent_run_min(activities, end=today) if activities else None
    if longest:
        long_run_cap = int(round(longest * MAX_LONG_RUN_SPIKE / 5.0) * 5)
    sessions = _race_week_sessions() if phase == "race" else _allocate(target, phase, is_recovery, long_run_cap)
    lr = next((s for s in sessions if s["sport"] == "run" and s["role"] == "long"), None)
    if lr and long_run_cap and lr["minutes"] >= long_run_cap:
        reasons.append(f"Long run capped at {lr['minutes']} min = 110% of your longest run in the last 30 days ({longest:.0f} min); "
                       f"bigger single-session jumps raise injury risk ~1.6-2.3x.")

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
                         "title": "RACE DAY - Half Ironman 70.3", "duration_min": int(GOAL_TIME_H * 60), "intensity": "Race",
                         "description": f"Goal {_fmt_mmss(GOAL_TIME_H * 60)}: swim {GOAL['swim']} min ({RACE_PACE['swim']}), T1 {GOAL['t1']}, "
                                        f"bike {GOAL['bike']} min ({RACE_PACE['bike']}, Z3 - never Z4), T2 {GOAL['t2']}, "
                                        f"run {GOAL['run']} min ({RACE_PACE['run']}). "
                                        + ("First 2 miles of the run 15-25 s/mi slower than goal. " if UNITS == "imperial"
                                           else "First 3 km of the run 10-15 s/km slower than goal. ")
                                        + "90 g carbs/h on the bike, 60 g/h on the run.",
                         "emoji": SPORT_EMOJI["race"]})
    workouts.sort(key=lambda w: (w["date"], w["sport"] == "strength", w["sport"] == "run" and w["role"] == "brick"))

    focus = {
        "base": "Pyramidal: mostly Z1-Z2 with one tempo session per sport; build swim consistency and heavy strength.",
        "build": "Threshold work on the bike and run; long ride grows with a brick run after it. Practise 90+ g carbs/h.",
        "peak": f"Race-specific and polarised: long sessions at goal pace ({RACE_PACE['bike']} / {RACE_PACE['run']}), short Z5 work, bricks every weekend.",
        "taper": "Cut volume ~45%, keep intensity and session frequency. Sleep, hydrate, trust the work.",
        "race": "Stay sharp and calm. Short openers only. Race day is coming.",
    }[phase]
    return {
        "week_start": monday.isoformat(), "week_end": (monday + timedelta(days=6)).isoformat(),
        "phase": phase, "is_recovery": is_recovery, "weeks_to_race": this["weeks_to_race"],
        "target_hours": target, "planned_hours": round(sum(w["duration_min"] for w in workouts if w["sport"] != "race") / 60, 1),
        "focus": focus, "reasons": reasons, "workouts": workouts, "timeline": timeline,
    }
