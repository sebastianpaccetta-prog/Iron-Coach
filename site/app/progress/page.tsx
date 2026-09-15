import Countdown from "@/components/Countdown";
import { LoadChart, PlannedVsActualChart, RecoveryChart, WeeklyVolumeChart } from "@/components/Charts";
import { data, fmtDate, fmtHours } from "@/lib/data";

export default function Progress() {
  const last4 = data.weekly.slice(-4);
  const avgHours = last4.reduce((s, w) => s + w.total_hours, 0) / Math.max(1, last4.length);
  const totals = data.weekly.reduce(
    (acc, w) => {
      for (const s of ["swim", "bike", "run"] as const) acc[s] += w.by_sport[s].km;
      return acc;
    },
    { swim: 0, bike: 0, run: 0 }
  );
  const z = data.zones;

  return (
    <>
      <div className="hero">
        <div>
          <span className="pill">{data.race.name}</span>
          <div className="meta" style={{ marginTop: 8, fontSize: 18 }}>{fmtDate(data.race.date, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}</div>
        </div>
        <div className="right"><Countdown /></div>
      </div>

      <div className="grid grid-4" style={{ marginTop: 16 }}>
        <div className="card stat accent"><span className="label">Fitness (CTL)</span><span className="value">{Math.round(data.fitness.ctl)}</span><span className="hint">42-day load average</span></div>
        <div className="card stat"><span className="label">Fatigue (ATL)</span><span className="value">{Math.round(data.fitness.atl)}</span><span className="hint">7-day load average</span></div>
        <div className="card stat"><span className="label">Form (TSB)</span><span className="value">{Math.round(data.fitness.tsb)}</span><span className="hint">{data.fitness.tsb > 5 ? "Fresh" : data.fitness.tsb < -20 ? "Fatigued" : "Training"}</span></div>
        <div className="card stat"><span className="label">Avg / week (4w)</span><span className="value">{fmtHours(avgHours)}</span><span className="hint">{Math.round(totals.bike)} km bike · {Math.round(totals.run)} km run · {Math.round(totals.swim * 1000) / 1000} km swim (20w)</span></div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Weekly volume by sport</h2>
        <WeeklyVolumeChart />
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h2>Training load trend</h2>
          <LoadChart />
        </div>
        <div className="card">
          <h2>Completed vs planned hours</h2>
          <PlannedVsActualChart />
        </div>
      </div>

      <div className="grid grid-3" style={{ marginTop: 16 }}>
        <div className="card"><h3>HRV (ms)</h3><RecoveryChart metric="hrv" color="#0284C7" unit="ms" /></div>
        <div className="card"><h3>Resting HR (bpm)</h3><RecoveryChart metric="resting_hr" color="#F26522" unit="bpm" /></div>
        <div className="card"><h3>Sleep (hours)</h3><RecoveryChart metric="sleep_hours" color="#7C3AED" unit="h" /></div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h2>Run zones (LTHR {z.run.lthr} bpm · threshold {z.run.threshold_pace ?? "–"}/km)</h2>
          <table className="zones-table">
            <thead><tr><th>Zone</th><th>Name</th><th>HR</th><th>Pace</th></tr></thead>
            <tbody>
              {z.run.hr_zones.map((hz: any, i: number) => (
                <tr key={hz.zone}>
                  <td><b>{hz.zone}</b></td><td>{hz.name}</td><td>{hz.low}–{hz.high}</td>
                  <td>{z.run.pace_zones ? `${z.run.pace_zones[i].slow}–${z.run.pace_zones[i].fast}` : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h2>Bike zones (LTHR {z.bike.lthr} bpm{z.bike.ftp ? ` · FTP ${z.bike.ftp} W` : ""})</h2>
          <table className="zones-table">
            <thead><tr><th>Zone</th><th>Name</th><th>HR</th></tr></thead>
            <tbody>
              {z.bike.hr_zones.map((hz: any) => (
                <tr key={hz.zone}><td><b>{hz.zone}</b></td><td>{hz.name}</td><td>{hz.low}–{hz.high}</td></tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: 12, color: "#8a8a8a", marginBottom: 0 }}>Max HR {z.max_hr}{z.resting_hr ? ` · resting ${Math.round(z.resting_hr)}` : ""}. Estimated from your history; edit in pipeline/zones.py.</p>
        </div>
      </div>
    </>
  );
}
