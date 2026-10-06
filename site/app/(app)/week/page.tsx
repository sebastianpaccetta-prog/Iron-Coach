import Countdown from "@/components/Countdown";
import Photo from "@/components/Photo";
import StatRow from "@/components/StatRow";
import WorkoutRow from "@/components/WorkoutRow";
import { data, fmtDate, fmtHours } from "@/lib/data";
import weekImg from "@/public/images/week.jpg";

export default function ThisWeek() {
  const wk = data.this_week;
  const ev = wk.evaluation;
  const workouts = ev
    ? wk.workouts.map((w) => {
        const e = ev.workouts.find((x) => x.date === w.date && x.sport === w.sport && x.title === w.title);
        return e ? { ...w, completed: e.completed, actual_min: e.actual_min } : w;
      })
    : wk.workouts;
  const planned = workouts.filter((w) => !["rest", "race", "strength"].includes(w.sport));
  const done = planned.filter((w) => w.completed).length;
  const lw = data.last_week;
  const rec = data.recovery_status;
  const ctlDelta = data.fitness.ctl_4w_ago != null ? Math.round(data.fitness.ctl - data.fitness.ctl_4w_ago) : null;

  return (
    <>
      <section className="banner photo">
        <Photo src={weekImg} position="center 42%" priority sizes="(max-width: 1160px) 100vw, 1120px" />
        <div className="banner-inner">
          <div>
            <p className="eyebrow">
              {wk.phase[0].toUpperCase() + wk.phase.slice(1)} phase{wk.is_recovery ? " · deload week" : ""} · {wk.weeks_to_race} weeks to go
            </p>
            <h1 className="display">
              {wk.start_date && wk.start_date !== wk.week_start
                ? `Starts ${fmtDate(wk.start_date, { weekday: "long", month: "long", day: "numeric" })}`
                : `Week of ${fmtDate(wk.week_start, { month: "long", day: "numeric" })}`}
            </h1>
            <p className="banner-sub">{fmtHours(wk.planned_hours)} planned · {wk.focus}</p>
          </div>
          <Countdown />
        </div>
      </section>

      <div className="panel">
        <StatRow
          stats={[
            { label: "This week", value: done, unit: `/ ${planned.length} done`, accent: true },
            {
              label: "Last week",
              value: lw ? lw.completed_sessions : "–",
              unit: lw ? `/ ${lw.planned_sessions}` : undefined,
              sub: lw ? `${fmtHours(lw.actual_hours)} of ${fmtHours(lw.planned_hours)}` : "First planned week",
            },
            {
              label: "Fitness",
              value: Math.round(data.fitness.ctl),
              sub: ctlDelta != null ? `${ctlDelta >= 0 ? "+" : "−"}${Math.abs(ctlDelta)} in 4 weeks` : `Form ${Math.round(data.fitness.tsb)}`,
            },
            {
              label: "Recovery",
              value: <span className={`flag ${rec.flag}`}>{rec.flag}</span>,
              sub: [
                rec.hrv_7d ? `HRV ${rec.hrv_7d} ms` : "",
                rec.resting_hr_7d ? `RHR ${Math.round(rec.resting_hr_7d)}` : "",
                rec.sleep_7d ? `${rec.sleep_7d}h sleep` : "",
              ].filter(Boolean).join(" · ") || "No Apple Health data",
            },
          ]}
        />
      </div>

      <div className="two-col">
        <section>
          <h2 className="section-title">Workouts</h2>
          <div className="workouts">
            {workouts.map((w, i) => (
              <WorkoutRow key={i} w={w} />
            ))}
          </div>
        </section>
        <aside>
          <h2 className="section-title">Why this week</h2>
          <ul className="reasons">
            {wk.reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </aside>
      </div>

      {lw && (
        <section>
          <h2 className="section-title">
            Last week <span className="muted">{lw.completed_sessions} of {lw.planned_sessions} sessions</span>
          </h2>
          <div className="workouts compact">
            {lw.workouts.map((w, i) => (
              <WorkoutRow key={i} w={w} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
