import SportIcon from "@/components/SportIcon";
import StatRow, { Stat } from "@/components/StatRow";
import { data, fmtDate, fmtMin, SPORT_COLOR, SPORT_LABEL } from "@/lib/data";

export default function Feed() {
  return (
    <>
      <header className="page-head">
        <h1 className="display">Activities</h1>
        <p>Your last {data.feed.length} workouts, straight from Strava.</p>
      </header>
      <div className="feed">
        {data.feed.map((a) => {
          const color = SPORT_COLOR[a.sport] ?? SPORT_COLOR.other;
          const stats: Stat[] = [];
          if (a.distance > 0) stats.push({ label: "Distance", value: a.distance.toFixed(2), unit: data.units.dist });
          if (a.pace) stats.push({ label: "Pace", value: a.pace.split(" ")[0], unit: a.pace.split(" ")[1] });
          if (a.speed) stats.push({ label: "Speed", value: a.speed, unit: data.units.speed });
          stats.push({ label: "Time", value: fmtMin(a.duration_min) });
          if (a.elevation_m > 0)
            stats.push(data.units.dist === "mi"
              ? { label: "Elev gain", value: Math.round(a.elevation_m * 3.28084), unit: "ft" }
              : { label: "Elev gain", value: a.elevation_m, unit: "m" });
          if (a.avg_hr) stats.push({ label: "Avg HR", value: Math.round(a.avg_hr), unit: "bpm" });
          if (a.avg_power) stats.push({ label: "Power", value: Math.round(a.avg_power), unit: "W" });
          if (a.tss != null) stats.push({ label: "Load", value: Math.round(a.tss) });
          return (
            <article className="activity" key={a.id}>
              <div className="activity-head">
                <span className="sport-badge" style={{ color, background: `${color}14` }}>
                  <SportIcon sport={a.sport} size={18} />
                </span>
                <div>
                  <span className="kind">{SPORT_LABEL[a.sport] ?? a.sport}</span>
                  <time>
                    {fmtDate(a.date, { weekday: "long", month: "long", day: "numeric", year: "numeric" })} at {a.start_time.slice(0, 5)}
                  </time>
                </div>
              </div>
              <h2>{a.name}</h2>
              <StatRow size="sm" stats={stats} />
            </article>
          );
        })}
      </div>
    </>
  );
}
