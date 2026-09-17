# How to send your training updates to Iron Coach

There is no upload on the website. The site is a static page that Vercel rebuilds
from a data file this project generates on your PC. So the weekly routine is:

**export -> drop the folder in -> run one command.** About 5 minutes, ideally Sunday.

## 1. Export from Strava (required)

1. On a computer: strava.com -> profile picture (top right) -> **Settings** ->
   **My Account** -> *Download or Delete Your Account* -> **Get Started** ->
   step 2 **Request Your Archive**.
2. Strava emails you a link within a few minutes to a few hours. Download the zip
   (`export_12345678.zip`).
3. Unzip it. You get a folder with `activities.csv` at the top level plus lots of other
   CSVs and an `activities/` folder of raw files. Only `activities.csv` is used.

## 2. Export from Apple Health (optional - gives HRV / resting HR / sleep)

1. iPhone -> **Health** app -> profile picture (top right) -> **Export All Health Data**
   -> Export. It takes 1-5 minutes and produces `export.zip` (can be 500 MB+).
2. AirDrop / iCloud / cable it to the PC and unzip. Inside is a folder
   `apple_health_export` containing `export.xml`.

If you skip this step, run the pipeline with `--feel good|normal|tired` instead and it
uses your self-report in place of the recovery metrics.

## 3. Drop the folders into the project

Put the unzipped folders anywhere in these spots:

```
Iron Coach/
  data/strava/activities.csv              <- Strava (this is what you have now)
  strava_export_2026-09-28/activities.csv <- or a dated folder at the top level
  data/apple_health/export.xml            <- Apple Health
  apple_health_export_2026-09-28/export.xml  <- or a dated folder at the top level
```

**Naming**: the folder name only needs to *start with* `strava_export` or
`apple_health_export`. What comes after is for you - a date like `2026-09-28`
(year-month-day) keeps them sorting properly in Explorer. Dropping the unzipped
`apple_health_export` folder straight in (no date) also works.

**Which one is used**: the pipeline reads whichever `activities.csv` / `export.xml` was
modified most recently, across all of those locations, and prints the path it picked
(`reading C:\...\activities.csv`). So a fresh export always wins. You can delete old
export folders any time; everything already imported lives in `data/normalized.db`.
Old activities are never lost - each export is deduplicated against the database.

Easiest habit: overwrite `data/strava` and `data/apple_health` each week and never
think about names.

## 4. Run the pipeline

Open a terminal in the `Iron Coach` folder (right-click -> *Open in Terminal*) and run:

```
python sunday.py --push
```

That parses the exports, updates the database, generates next week's plan, writes the
Google Calendar events, regenerates the site data, commits and pushes. Vercel rebuilds
the website within a minute or two.

Useful variants:

```
python sunday.py                     # everything except the push - review first, then git push
python sunday.py --push --feel tired # no Apple Health export this week; ask for a lighter week
python sunday.py --dry-run           # just print the plan, change nothing
python sunday.py --no-calendar       # skip Google Calendar
```

The end of the output is the summary: last week's completion, fitness trend, the
goal-pace check, and the week ahead.

## Checklist

- [ ] Strava archive requested and unzipped
- [ ] (optional) Apple Health export unzipped
- [ ] Folders dropped into `Iron Coach/` (see section 3)
- [ ] `python sunday.py --push`
- [ ] Output says `reading ...` with today's export, and `N new` activities > 0
- [ ] Website shows the new week (hard-refresh if it looks stale)

## Troubleshooting

* **`0 new` activities** - the export you dropped in is older than what is already in the
  database, or the pipeline picked an old folder. Check the `reading ...` line; delete
  stale export folders.
* **Nothing about HRV in the summary** - Apple Health export missing or older than 7 days.
  Use `--feel`.
* **Push rejected (email privacy)** - run
  `git config user.email "sebastianpaccetta-prog@users.noreply.github.com"` once.
* **Vercel didn't rebuild** - check `git log -1` was pushed (`git status` says "up to
  date with origin/main"); otherwise `git push`.
