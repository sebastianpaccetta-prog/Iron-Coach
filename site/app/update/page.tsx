const STEPS = [
  {
    n: 1,
    title: "Export from Strava",
    tag: "required",
    body: (
      <ol>
        <li>On a computer go to <b>strava.com</b> → profile picture (top right) → <b>Settings</b> → <b>My Account</b>.</li>
        <li>Under <i>Download or Delete Your Account</i> click <b>Get Started</b>, then step 2 <b>Request Your Archive</b>.</li>
        <li>Strava emails a download link (minutes to a few hours). Download the zip and <b>unzip it</b>.</li>
        <li>The unzipped folder has <code>activities.csv</code> at the top level. That is the only file the coach reads.</li>
      </ol>
    ),
  },
  {
    n: 2,
    title: "Export from Apple Health",
    tag: "optional · HRV, resting HR, sleep",
    body: (
      <>
        <ol>
          <li>iPhone → <b>Health</b> app → profile picture (top right) → <b>Export All Health Data</b> → Export.</li>
          <li>Wait 1–5 minutes; it produces <code>export.zip</code> (often 500 MB+).</li>
          <li>AirDrop / iCloud / cable it to the PC and unzip. Inside is a folder <code>apple_health_export</code> containing <code>export.xml</code>.</li>
        </ol>
        <p className="note">Skipping this week? Run the pipeline with <code>--feel good</code>, <code>--feel normal</code> or <code>--feel tired</code> and the coach uses your self-report instead of the recovery metrics.</p>
      </>
    ),
  },
  {
    n: 3,
    title: "Drop the folders into the project",
    tag: "any of these locations",
    body: (
      <>
        <pre>{`Iron Coach/
  data/strava/activities.csv                   ← Strava (what you have now)
  strava_export_2026-09-28/activities.csv      ← or a dated folder at the top level
  data/apple_health/export.xml                 ← Apple Health
  apple_health_export_2026-09-28/export.xml    ← or a dated folder at the top level`}</pre>
        <ul>
          <li><b>Naming:</b> the folder only has to <i>start with</i> <code>strava_export</code> or <code>apple_health_export</code>. Add a date as <code>YYYY-MM-DD</code> so folders sort in order. Dropping the unzipped <code>apple_health_export</code> folder in as-is also works.</li>
          <li><b>Which one gets used:</b> whichever <code>activities.csv</code> / <code>export.xml</code> was modified most recently, across all those spots. A fresh export always wins. The pipeline prints the path it picked.</li>
          <li><b>Old folders:</b> safe to delete any time. Everything already imported lives in <code>data/normalized.db</code> and each export is de-duplicated against it — nothing is lost.</li>
          <li><b>Easiest habit:</b> overwrite <code>data/strava</code> and <code>data/apple_health</code> each week and never name anything.</li>
        </ul>
      </>
    ),
  },
  {
    n: 4,
    title: "Run the pipeline",
    tag: "one command",
    body: (
      <>
        <p>Open a terminal in the <code>Iron Coach</code> folder (right-click the folder → <i>Open in Terminal</i>) and run:</p>
        <pre className="cmd">python sunday.py --push</pre>
        <p>That parses the exports, updates the database, generates next week&apos;s plan, writes the Google Calendar events, regenerates this site&apos;s data, commits and pushes. Vercel rebuilds the website in a minute or two.</p>
        <table className="cmd-table">
          <tbody>
            <tr><td><code>python sunday.py</code></td><td>everything except the push — review, then <code>git push</code></td></tr>
            <tr><td><code>python sunday.py --push --feel tired</code></td><td>no Apple Health export; ask for a lighter week</td></tr>
            <tr><td><code>python sunday.py --dry-run</code></td><td>just print the plan, change nothing</td></tr>
            <tr><td><code>python sunday.py --no-calendar</code></td><td>skip Google Calendar</td></tr>
          </tbody>
        </table>
      </>
    ),
  },
];

const CHECKLIST = [
  "Strava archive requested and unzipped",
  "(optional) Apple Health export unzipped",
  "Folders dropped into Iron Coach/ (step 3)",
  "python sunday.py --push",
  "Output shows “reading …” with today’s export and N new activities > 0",
  "This site shows the new week (hard-refresh if it looks stale)",
];

const TROUBLE = [
  { q: "0 new activities", a: "The export is older than what's already in the database, or an old folder was picked. Check the “reading …” line and delete stale export folders." },
  { q: "No HRV line in the summary", a: "Apple Health export missing or older than 7 days. Use --feel." },
  { q: "Push rejected (email privacy)", a: "Run once: git config user.email \"sebastianpaccetta-prog@users.noreply.github.com\"" },
  { q: "Site didn't update", a: "git status should say “up to date with origin/main”; otherwise git push. Then hard-refresh." },
];

export default function Update() {
  return (
    <>
      <h1 className="page-title">How to update</h1>
      <p className="page-sub">
        There is no upload on this site — it is rebuilt from a data file your PC generates. The weekly routine is
        <b> export → drop the folder in → run one command</b>. About 5 minutes, ideally Sunday.
      </p>

      <div className="steps">
        {STEPS.map((s) => (
          <div className="card step" key={s.n}>
            <div className="step-head">
              <span className="step-num">{s.n}</span>
              <h2>{s.title}</h2>
              <span className="pill dark">{s.tag}</span>
            </div>
            <div className="step-body">{s.body}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h2>Sunday checklist</h2>
          <ul className="checklist">
            {CHECKLIST.map((c) => <li key={c}><span className="box" />{c}</li>)}
          </ul>
        </div>
        <div className="card">
          <h2>Troubleshooting</h2>
          <dl className="trouble">
            {TROUBLE.map((t) => (
              <div key={t.q}><dt>{t.q}</dt><dd>{t.a}</dd></div>
            ))}
          </dl>
        </div>
      </div>
    </>
  );
}
