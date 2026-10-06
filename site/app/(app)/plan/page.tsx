import { data, fmtDate, fmtHours, PHASE_COLOR } from "@/lib/data";

const PHASE_INFO: Record<string, string> = {
  base: "Aerobic foundation, swim frequency, strength. Mostly Z2.",
  build: "Threshold intervals on bike and run, long ride grows, first bricks.",
  peak: "Race-specific long sessions at 70.3 effort, biggest weeks.",
  taper: "Volume drops, intensity stays. Arrive fresh.",
  race: "Openers only. Race day.",
};

export default function PlanOverview() {
  const tl = data.timeline;
  const maxH = Math.max(...tl.map((t) => t.target_hours), 1);
  const phases = Array.from(new Set(tl.map((t) => t.phase)));
  const counts = phases.map((p) => ({ p, n: tl.filter((t) => t.phase === p).length }));

  return (
    <>
      <header className="page-head">
        <h1 className="display">Season plan</h1>
        <p>
          {tl.length} weeks from {fmtDate(tl[0].week_start, { month: "long", day: "numeric" })} to race day,{" "}
          {fmtDate(data.race.date, { month: "long", day: "numeric", year: "numeric" })}. Targets ramp at most 10% a week with a
          deload every 4th week; each Sunday the coming week is re-planned from what you actually did.
        </p>
      </header>

      <section className="panel">
        <div className="season" aria-label="Weekly target hours">
          {tl.map((t, i) => (
            <div key={t.week_start} className={`season-col${i === 0 ? " current" : ""}`} title={`${fmtDate(t.week_start, { month: "short", day: "numeric" })} · ${t.phase} · ${fmtHours(t.target_hours)}`}>
              <span className="season-h">{Math.round(t.target_hours)}</span>
              <div className="season-bar" style={{ height: `${(t.target_hours / maxH) * 100}%`, background: PHASE_COLOR[t.phase], opacity: t.is_recovery ? 0.45 : 1 }} />
            </div>
          ))}
        </div>
        <div className="season-axis">
          {counts.map(({ p, n }) => (
            <div key={p} style={{ flex: n }}>
              <i style={{ background: PHASE_COLOR[p] }} />
              <span>{p}</span>
            </div>
          ))}
        </div>
        <p className="fine">Bars are target hours per week. Faded bars are deload weeks.</p>
      </section>

      <div className="phase-cards">
        {phases.map((p) => (
          <div key={p}>
            <h3><i style={{ background: PHASE_COLOR[p] }} />{p}</h3>
            <p>{PHASE_INFO[p]}</p>
          </div>
        ))}
      </div>

      <section className="panel">
        <h2 className="panel-title">Week by week</h2>
        <div className="timeline">
          {tl.map((t, i) => (
            <div key={t.week_start} className={`tl-row${i === 0 ? " current" : ""}`}>
              <div className="tl-date">{fmtDate(t.week_start, { month: "short", day: "numeric" })}</div>
              <div className="tl-phase">{t.phase}{t.is_recovery ? " · deload" : ""}</div>
              <div className="tl-bar"><span style={{ width: `${(t.target_hours / maxH) * 100}%`, background: PHASE_COLOR[t.phase], opacity: t.is_recovery ? 0.5 : 1 }} /></div>
              <div className="tl-hours">{fmtHours(t.target_hours)}</div>
            </div>
          ))}
          <div className="tl-row race">
            <div className="tl-date">{fmtDate(data.race.date, { month: "short", day: "numeric" })}</div>
            <div className="tl-phase">Race day</div>
            <div />
            <div />
          </div>
        </div>
      </section>
    </>
  );
}
