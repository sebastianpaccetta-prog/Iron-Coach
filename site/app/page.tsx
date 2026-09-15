import Countdown from "@/components/Countdown";
import WorkoutRow from "@/components/WorkoutRow";
import { data, fmtDate, fmtHours } from "@/lib/data";

export default function ThisWeek() {
  const wk = data.this_week;
  const ev = wk.evaluation;
  const workouts = ev
    ? wk.workouts.map((w) => {
        const e = ev.workouts.find((x) => x.date === w.date && x.sport === w.sport && x.title === w.title);
        return e ? { ...w, completed: e.completed, actual_min: e.actual_min } : w;
      })
    : wk.workouts;
  const planned = workouts.filter((w) => w.sport !== "rest" && w.sport !== "race");
  const done = planned.filter((w) => w.completed).length;
  const lw = data.last_week;
  const recFlag = data.recovery_status.flag;

  return (
    <>
      <div className="hero">
        <div>
          <span className="pill">{wk.phase}{wk.is_recovery ? " · deload" : ""}</span>
          <div className="big" style={{ marginTop: 8 }}>
            {fmtHours(wk.planned_hours)}
            <small>planned</small>
          </div>
          <div className="meta">Week of {fmtDate(wk.week_start, { month: "long", day: "numeric" })} · {wk.weeks_to_race} weeks to go</div>
        </div>
        <div className="right">
          <Countdown />
          <div className="meta">{data.race.name} · {fmtDate(data.race.date, { month: "long", day: "numeric", year: "numeric" })}</div>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginTop: 16 }}>
        <div className="card stat accent">
          <span className="label">This week</span>
          <span className="value">{done}<small>/ {planned.length} done</small></span>
          <span className="hint">{wk.focus}</span>
        </div>
        <div className="card stat">
          <span className="label">Last week</span>
          <span className="value">
            {lw ? `${lw.completed_sessions}` : "–"}
            <small>{lw ? `/ ${lw.planned_sessions} sessions` : "no plan yet"}</small>
          </span>
          <span className="hint">{lw ? `${fmtHours(lw.actual_hours)} of ${fmtHours(lw.planned_hours)} planned` : "First planned week"}</span>
        </div>
        <div className="card stat">
          <span className="label">Fitness (CTL)</span>
          <span className="value">
            {Math.round(data.fitness.ctl)}
            <small>
              {data.fitness.ctl_4w_ago != null
                ? `${data.fitness.ctl - data.fitness.ctl_4w_ago >= 0 ? "▲" : "▼"} ${Math.abs(Math.round(data.fitness.ctl - data.fitness.ctl_4w_ago))} vs 4w`
                : ""}
            </small>
          </span>
          <span className="hint">Form (TSB) {Math.round(data.fitness.tsb)}</span>
        </div>
        <div className="card stat">
          <span className="label">Recovery</span>
          <span className="value">
            <span className={`pill ${recFlag === "good" ? "good" : recFlag === "caution" ? "bad" : "dark"}`}>{recFlag}</span>
          </span>
          <span className="hint">
            {data.recovery_status.hrv_7d ? `HRV ${data.recovery_status.hrv_7d} ms` : ""}
            {data.recovery_status.resting_hr_7d ? ` · RHR ${Math.round(data.recovery_status.resting_hr_7d)}` : ""}
            {data.recovery_status.sleep_7d ? ` · sleep ${data.recovery_status.sleep_7d}h` : ""}
          </span>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Why this week looks like this</h2>
        <ul className="reasons">
          {wk.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>

      <h2 className="page-title" style={{ fontSize: 20 }}>Workouts</h2>
      <div className="workouts">
        {workouts.map((w, i) => (
          <WorkoutRow key={i} w={w} />
        ))}
      </div>

      {lw && (
        <>
          <h2 className="page-title" style={{ fontSize: 20 }}>Last week review</h2>
          <div className="workouts">
            {lw.workouts.map((w, i) => (
              <WorkoutRow key={i} w={w} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
