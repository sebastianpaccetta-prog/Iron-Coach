"""Iron Coach weekly pipeline. Run every Sunday:

    python sunday.py                 # parse -> analyze -> plan -> calendar -> site data
    python sunday.py --push          # ...and git commit + push (triggers Vercel deploy)
    python sunday.py --no-calendar   # skip Google Calendar sync
    python sunday.py --dry-run       # plan only, write nothing to calendar/site

Steps: 1 parse new Strava + Apple Health data  2 update SQLite  3 compute load,
zones and recovery  4 generate next week's plan  5 sync Google Calendar
6 write site/public/data.json  7 optional commit + push.
"""
import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta

from pipeline import db
from pipeline.config import DB_PATH, PLAN_OUTPUT_PATH, RACE_DATE, ROOT
from pipeline.parse_apple_health import load_apple_health
from pipeline.parse_strava import load_strava
from pipeline.plan import evaluate_completion, generate_week, upcoming_monday
from pipeline.site_export import export_site_data
from pipeline.training_load import activity_tss, load_series, recovery_status, weekly_summary
from pipeline.zones import build_zones


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which cannot print emoji


def step(msg):
    print(f"\n==> {msg}")


def main():
    ap = argparse.ArgumentParser(description="Iron Coach Sunday pipeline")
    ap.add_argument("--push", action="store_true", help="git commit + push after generating")
    ap.add_argument("--no-calendar", action="store_true", help="skip Google Calendar sync")
    ap.add_argument("--dry-run", action="store_true", help="do not write calendar, site data or plan")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD) for testing")
    ap.add_argument("--feel", choices=["good", "normal", "tired"],
                    help="how you feel this week; overrides the Apple Health recovery flag "
                         "(tired = lighter week, no hard intervals)")
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()

    with db.connect() as conn:
        # 1-2. Parse and store new data -------------------------------------
        step("Parsing Strava export")
        strava_rows = load_strava()
        inserted = db.upsert_activities(conn, strava_rows)
        print(f"   {len(strava_rows)} activities in export, {inserted} new")

        step("Parsing Apple Health export (streaming)")
        health_rows = load_apple_health()
        db.upsert_recovery(conn, health_rows)
        print(f"   {len(health_rows)} recovery records upserted")

        # 3. Analyse ----------------------------------------------------------
        step("Analysing training load and zones")
        activities = db.fetch_activities(conn)
        recovery = db.fetch_recovery(conn, since=today - timedelta(days=180))
        rec_status = recovery_status(recovery, end=today)
        if args.feel:
            rec_status["flag"] = {"good": "good", "normal": "normal", "tired": "caution"}[args.feel]
            rec_status["reasons"] = [f"you reported feeling {args.feel}"]
        zones = build_zones(activities, resting_hr=rec_status.get("resting_hr_7d"))
        for a in activities:
            a["tss"] = activity_tss(a, zones)
        conn.executemany("UPDATE activities SET tss = ? WHERE id = ?", [(a["tss"], a["id"]) for a in activities])
        load = load_series(activities, end=today)
        weekly = weekly_summary(activities, weeks=20, end=today)
        print(f"   Run LTHR {zones['run']['lthr']} bpm | Bike LTHR {zones['bike']['lthr']} bpm | "
              f"Max HR {zones['max_hr']} | Threshold pace {zones['run']['threshold_pace']} /km")
        print(f"   CTL {load[-1]['ctl']} | ATL {load[-1]['atl']} | TSB {load[-1]['tsb']} | Recovery: {rec_status['flag']}")

        # 4. Evaluate last week, generate next --------------------------------
        step("Generating next week's plan")
        monday = upcoming_monday(today)
        last_monday = monday - timedelta(days=7)
        last_plan_json = db.get_plan(conn, last_monday.isoformat())
        last_eval = evaluate_completion(json.loads(last_plan_json), activities) if last_plan_json else None
        plan = generate_week(today, weekly, load, rec_status, zones, last_eval)
        if not args.dry_run:
            db.save_plan(conn, plan["week_start"], json.dumps(plan), datetime.now().isoformat())
            PLAN_OUTPUT_PATH.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
        # If today is inside the planned week, show progress on it too.
        this_eval = evaluate_completion(plan, activities) if monday <= today else None

        # 5. Calendar -----------------------------------------------------------
        if not args.no_calendar and not args.dry_run:
            step("Syncing Google Calendar")
            try:
                from pipeline.calendar_sync import sync_week
                n = sync_week(plan)
                print(f"   {n} events written to the 'Iron Coach' calendar")
            except FileNotFoundError as e:
                print(f"   Skipped: {e}")
            except Exception as e:  # keep the pipeline going even if Google is down
                print(f"   Calendar sync failed: {e}")

        # 6. Site data ------------------------------------------------------------
        if not args.dry_run:
            step("Writing site data")
            export_site_data(plan, last_eval, activities, weekly, load, recovery, rec_status, zones, this_eval)
            print("   site/public/data.json updated")

    # 7. Push ----------------------------------------------------------------------
    if args.push and not args.dry_run:
        step("Committing and pushing")
        subprocess.run(["git", "add", "site/public/data.json", "data/plan.json"], cwd=ROOT, check=False)
        subprocess.run(["git", "commit", "-m", f"Weekly update {plan['week_start']}"], cwd=ROOT, check=False)
        subprocess.run(["git", "push"], cwd=ROOT, check=False)

    print_summary(plan, last_eval, load, weekly, rec_status, today)


def print_summary(plan, last_eval, load, weekly, rec_status, today):
    print("\n" + "=" * 64)
    print(f"  IRON COACH  |  {(RACE_DATE - today).days} days to race  |  week of {plan['week_start']}")
    print("=" * 64)
    if last_eval:
        print(f"Last week: {last_eval['completed_sessions']}/{last_eval['planned_sessions']} sessions, "
              f"{last_eval['actual_hours']} h of {last_eval['planned_hours']} h planned")
    else:
        lw = weekly[-2] if len(weekly) >= 2 else None
        if lw:
            print(f"Last week: {lw['sessions']} sessions, {lw['total_hours']} h (no plan on record yet)")
    ctl_now = load[-1]["ctl"]
    ctl_prev = load[-29]["ctl"] if len(load) > 29 else ctl_now
    trend = "rising" if ctl_now > ctl_prev + 1 else ("falling" if ctl_now < ctl_prev - 1 else "flat")
    print(f"Fitness: CTL {ctl_now:.0f} ({trend} vs 4 wks ago {ctl_prev:.0f}), form TSB {load[-1]['tsb']:.0f}, recovery {rec_status['flag']}")
    print(f"\nThis week: {plan['phase'].upper()}{' (DELOAD)' if plan['is_recovery'] else ''} - {plan['planned_hours']} h planned")
    print(f"Focus: {plan['focus']}")
    for r in plan["reasons"]:
        print(f" - {r}")
    print()
    for w in plan["workouts"]:
        dur = f"{w['duration_min']} min" if w["duration_min"] else ""
        print(f"  {w['date']} {w['weekday'][:3]}  {w['emoji']} {w['title']:<40} {dur:>8}  {w['intensity']}")
    print()


if __name__ == "__main__":
    sys.exit(main())
