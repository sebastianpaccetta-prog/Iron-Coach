# Iron Coach

A personal triathlon coach for a Half Ironman 70.3 on **1 February 2027**. Every Sunday you drop
your latest Strava (and optionally Apple Health) export in the folder, run one command, and it:

1. parses the new activities and recovery metrics into a small SQLite database,
2. works out your training load (TSS-style), fitness/fatigue trend and heart-rate zones,
3. writes next week's plan (Mon-Sun) with a short explanation of *why*,
4. pushes every workout to a dedicated **"Iron Coach"** Google Calendar as all-day events,
5. refreshes the website data so a `git push` redeploys the dashboard on Vercel.

```
Iron Coach/
├── sunday.py               <- the one command
├── pipeline/               <- Python modules (parsing, load, plan, calendar, site export)
│   ├── config.py           <- race date, paths, calendar name
│   ├── plan.py             <- ALL the coaching constants live at the top of this file
│   ├── zones.py            <- HR / pace zone estimation
│   └── training_load.py    <- TSS, CTL/ATL/TSB, weekly totals, recovery flags
├── data/
│   ├── strava/             <- unzip the Strava export here (activities.csv + activities/)
│   ├── apple_health/       <- unzip the Apple Health export here (export.xml)
│   ├── normalized.db       <- generated SQLite (gitignored)
│   └── plan.json           <- this week's plan
└── site/                   <- Next.js dashboard, reads site/public/data.json
```

## One-time setup

### 1. Python

```powershell
python -m pip install -r requirements.txt
```

(Python 3.10+; only the Google Calendar client libraries are needed, everything else is stdlib.)

### 2. Your data

* **Strava**: Settings -> My Account -> *Download or Delete Your Account* -> *Request Your Archive*.
  Unzip it and put the contents in `data/strava/` so that `data/strava/activities.csv` exists.
  (A folder named `strava_export_*` in the project root also works.)
* **Apple Health** (optional): Health app -> profile picture -> *Export All Health Data*.
  Unzip and put `export.xml` in `data/apple_health/` (or leave the `apple_health_export_*`
  folder in the project root). The file is streamed, so its size does not matter.

Only these are read: `activities.csv` from Strava and resting HR / HRV / sleep / VO2max
records from Apple Health. Everything else (raw .fit/.gpx files, clubs, followers, media,
clinical records, workout routes) is ignored.

### 3. Google Calendar

1. Go to <https://console.cloud.google.com/> and create a project (e.g. "Iron Coach").
2. *APIs & Services -> Library* -> search **Google Calendar API** -> **Enable**.
3. *APIs & Services -> OAuth consent screen* -> External -> fill in the app name and your email
   -> add yourself under **Test users** (this keeps the app in testing mode, which is fine
   for personal use).
4. *APIs & Services -> Credentials -> Create credentials -> OAuth client ID* ->
   Application type **Desktop app** -> Create -> **Download JSON**.
5. Save that file as `credentials.json` in the project root (next to `sunday.py`).

The first time you run the pipeline a browser window asks you to sign in and grant calendar
access; the resulting `token.json` is stored next to `credentials.json`. Both files are in
`.gitignore` - never commit them.

The pipeline creates a calendar called **Iron Coach** on the first run. In Google Calendar you
can toggle it on/off independently of your main calendar. Re-running for the same week
replaces that week's events (no duplicates).

### 4. Website on Vercel

```powershell
cd site
npm install
npm run dev        # http://localhost:3000 to preview
```

To deploy: push this repository to GitHub, then on <https://vercel.com> click *Add New
Project*, import the repo and set **Root Directory** to `site`. Every later `git push` triggers
a redeploy. The site is fully static; it reads `site/public/data.json`, which the Sunday
script regenerates. The site is public by design (no login).

## The Sunday routine

1. Download a fresh Strava export (and Apple Health export if you like) and replace the
   contents of `data/strava/` (and `data/apple_health/`).
2. Run:

   ```powershell
   python sunday.py --push
   ```

   Flags: `--no-calendar` skips Google Calendar, `--dry-run` only prints the plan,
   `--push` commits `site/public/data.json` + `data/plan.json` and pushes (which redeploys
   the site). Omit `--push` to review first and push manually.
   `--feel good|normal|tired` overrides the recovery flag - use `--feel tired` for a lighter
   week with no hard intervals. Handy if you skip the Apple Health export entirely.

3. Read the summary printed at the end: last week's completion, fitness trend, and the goals
   for the coming week. Open the calendar or the website for the details.

You can run it any day; if it is not Saturday/Sunday the plan is still generated for the
*next* Monday and "last week" means the last full week.

## How the plan is built

* **Phases** (measured backwards from race day, `pipeline/plan.py -> PHASES`):
  base (>15 weeks out), build (8 weeks), peak (4 weeks), taper (2 weeks), race week.
* **Volume**: next week = last week's actual hours x 1.10 at most, capped by the phase cap
  (`PEAK_WEEK_HOURS x PHASE_TARGET_FRACTION`). Every 4th week is a deload at 65%.
* **Adjustments**: if you completed fewer than 60% of last week's sessions the volume is held;
  if HRV is >10% below its 6-week baseline, resting HR is >4 bpm up, or sleep averages
  <6.5 h, the week is 15% lighter and hard sessions become easy; if form (TSB) is below -25
  another 10% comes off.
* **Sport split** by phase (`SPORT_SPLIT`) and a weekly template (`WEEK_TEMPLATE`):
  Mon swim + strength, Tue run quality, Wed bike quality, Thu swim, Fri easy run or rest,
  Sat long ride (+ brick run from build phase), Sun long run. Sessions under their minimum
  length are dropped, lowest priority first, when the weekly hours are small.
* **Zones**: run LTHR = average of your three highest 20-70 min average-HR runs in the last
  6 months, bike LTHR likewise (or run - 5), five zones as % of LTHR. Threshold pace from
  your best 20-70 min runs. Override anything in `pipeline/zones.py`.
* **Load**: TSS = hours x IF^2 x 100 with IF from power/FTP, HR/LTHR, RPE or a per-sport
  default. CTL = 42-day average, ATL = 7-day, TSB = CTL - ATL.

Tweak numbers at the top of `pipeline/plan.py`; nothing else needs to change.

## Troubleshooting

* *"credentials.json not found"* - finish step 3 of the setup, or run with `--no-calendar`.
* *Google says the app is unverified* - click *Advanced -> Go to Iron Coach (unsafe)*; it is
  your own app in testing mode.
* *Token expired / revoked* - delete `token.json` and run again.
* *Nothing new was inserted* - activities are deduplicated on date + start time + sport, so
  re-importing the same export is a no-op. That is expected.
