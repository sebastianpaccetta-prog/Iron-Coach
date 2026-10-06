import { LoadChart, PlannedVsActualChart, RecoveryChart, WeeklyVolumeChart } from "@/components/Charts";
import StatRow from "@/components/StatRow";
import { data, fmtDate, fmtHours } from "@/lib/data";

export default function Progress() {
  const last4 = data.weekly.slice(-4);
  const avgHours = last4.reduce((s, w) => s + w.total_hours, 0) / Math.max(1, last4.length);
  const totals = data.weekly.reduce(
    (acc, w) => {
      for (const s of ["swim", "bike", "run"] as const) acc[s] += w.by_sport[s].dist;
      return acc;
    },
    { swim: 0, bike: 0, run: 0 }
  );
  const z = data.zones;
  const u = data.units.dist;
  const tsb = data.fitness.tsb;

  return (
    <>
      <header className="page-head">
        <h1 className="display">Progress</h1>
        <p>
          {data.race.name} · {fmtDate(data.race.date, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
        </p>
      </header>

      <div className="panel">
        <StatRow
          stats={[
            { label: "Fitness (CTL)", value: Math.round(data.fitness.ctl), sub: "42-day load average", accent: true },
            { label: "Fatigue (ATL)", value: Math.round(data.fitness.atl), sub: "7-day load average" },
            { label: "Form (TSB)", value: Math.round(tsb), sub: tsb > 5 ? "Fresh" : tsb < -20 ? "Fatigued" : "Training" },
            { label: "Avg / week", value: fmtHours(avgHours), sub: "Last 4 weeks" },
          ]}
        />
        <StatRow
          size="sm"
          stats={[
            { label: "Swim · 20 wks", value: totals.swim.toFixed(1), unit: u },
            { label: "Bike · 20 wks", value: Math.round(totals.bike), unit: u },
            { label: "Run · 20 wks", value: Math.round(totals.run), unit: u },
          ]}
        />
      </div>

      <section className="panel">
        <h2 className="panel-title">Weekly volume by sport</h2>
        <WeeklyVolumeChart />
      </section>

      <div className="grid grid-2">
        <section className="panel">
          <h2 className="panel-title">Fitness, fatigue and form</h2>
          <LoadChart />
        </section>
        <section className="panel">
          <h2 className="panel-title">Completed vs planned hours</h2>
          <PlannedVsActualChart />
        </section>
      </div>

      <div className="grid grid-3">
        <section className="panel"><h2 className="panel-title sm">HRV <span className="muted">ms</span></h2><RecoveryChart metric="hrv" color="#2F7EC1" unit="ms" /></section>
        <section className="panel"><h2 className="panel-title sm">Resting HR <span className="muted">bpm</span></h2><RecoveryChart metric="resting_hr" color="#FC5200" unit="bpm" /></section>
        <section className="panel"><h2 className="panel-title sm">Sleep <span className="muted">hours</span></h2><RecoveryChart metric="sleep_hours" color="#1B998B" unit="h" /></section>
      </div>

      <div className="grid grid-2">
        <section className="panel">
          <h2 className="panel-title">Run zones</h2>
          <p className="panel-sub">{z.method_label} · {z.zones_source} · threshold pace {z.run.threshold_pace ?? "–"}/{u}</p>
          <table className="zones-table">
            <thead><tr><th>Zone</th><th>Name</th><th>HR</th><th>Pace</th></tr></thead>
            <tbody>
              {z.run.hr_zones.map((hz: any) => (
                <tr key={hz.zone}>
                  <td><b>{hz.zone}</b></td><td>{hz.name}</td><td>{hz.low}–{hz.high}</td>
                  <td>{(() => { const pz = z.run.pace_zones?.find((p: any) => p.zone === hz.zone); return pz ? `${pz.slow}–${pz.fast}` : "–"; })()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {z.run.lthr_source && <p className="fine">Estimated LTHR {z.run.lthr} (used for training load): {z.run.lthr_source}.</p>}
        </section>
        <section className="panel">
          <h2 className="panel-title">Bike zones</h2>
          <p className="panel-sub">{z.method_label} · {z.zones_source}{z.bike.ftp ? ` · FTP ${z.bike.ftp} W` : ""}</p>
          <table className="zones-table">
            <thead><tr><th>Zone</th><th>Name</th><th>HR</th></tr></thead>
            <tbody>
              {z.bike.hr_zones.map((hz: any) => (
                <tr key={hz.zone}><td><b>{hz.zone}</b></td><td>{hz.name}</td><td>{hz.low}–{hz.high}</td></tr>
              ))}
            </tbody>
          </table>
          {z.bike.lthr_source && <p className="fine">Estimated LTHR {z.bike.lthr} (used for training load): {z.bike.lthr_source}.</p>}
          <p className="fine">Max HR {z.max_hr}{z.max_hr_source ? ` (${z.max_hr_source})` : ""}{z.resting_hr ? ` · resting ${Math.round(z.resting_hr)}` : ""}.
            {" "}Know your max HR? Set MAX_HR under Athlete settings in pipeline/config.py.</p>
        </section>
      </div>
    </>
  );
}
