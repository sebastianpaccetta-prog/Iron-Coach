import { data, fmtDate, fmtHours } from "@/lib/data";

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
      <h1 className="page-title">Plan overview</h1>
      <p className="page-sub">
        {tl.length} weeks from {fmtDate(tl[0].week_start, { month: "long", day: "numeric" })} to race day,{" "}
        {fmtDate(data.race.date, { month: "long", day: "numeric", year: "numeric" })}. Targets are projected at a max +10% ramp per
        week with a deload every 4th week; each Sunday the coming week is re-planned from what you actually did.
      </p>

      <div className="card">
        <div className="phase-strip">
          {tl.map((t) => (
            <div key={t.week_start} className={`phase-${t.phase}`} style={{ opacity: t.is_recovery ? 0.45 : 1 }} title={`${t.week_start} · ${t.phase}`} />
          ))}
        </div>
        <div className="tl-legend" style={{ marginTop: 10 }}>
          {counts.map(({ p, n }) => (
            <span key={p}><i className={`phase-${p}`} /> {p} · {n} wk{n > 1 ? "s" : ""}</span>
          ))}
          <span><i style={{ background: "#ccc" }} /> lighter = deload</span>
        </div>
      </div>

      <div className="grid grid-3" style={{ marginTop: 16 }}>
        {phases.map((p) => (
          <div className="card" key={p}>
            <h3><span className={`pill dark`} style={{ marginRight: 8 }}>{p}</span></h3>
            <p style={{ margin: 0, fontSize: 14, color: "#5b5b5b" }}>{PHASE_INFO[p]}</p>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Week by week</h2>
        <div className="timeline">
          {tl.map((t, i) => (
            <div key={t.week_start} className={`tl-row ${i === 0 ? "current" : ""}`}>
              <div>{fmtDate(t.week_start, { month: "short", day: "numeric" })}</div>
              <div style={{ textTransform: "capitalize", fontSize: 13 }}>{t.phase}{t.is_recovery ? " ·↓" : ""}</div>
              <div className="tl-bar"><span className={`phase-${t.phase}`} style={{ width: `${(t.target_hours / maxH) * 100}%`, opacity: t.is_recovery ? 0.5 : 1 }} /></div>
              <div style={{ textAlign: "right", fontSize: 13 }}>{fmtHours(t.target_hours)}</div>
            </div>
          ))}
          <div className="tl-row" style={{ fontWeight: 800 }}>
            <div>{fmtDate(data.race.date, { month: "short", day: "numeric" })}</div>
            <div>🏁 Race</div>
            <div />
            <div />
          </div>
        </div>
      </div>
    </>
  );
}
