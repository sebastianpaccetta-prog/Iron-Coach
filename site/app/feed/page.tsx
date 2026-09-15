import { data, fmtDate, fmtMin, SPORT_COLOR, SPORT_EMOJI } from "@/lib/data";

export default function Feed() {
  return (
    <>
      <h1 className="page-title">Activity feed</h1>
      <p className="page-sub">Your last {data.feed.length} completed workouts, straight from Strava.</p>
      <div className="grid" style={{ gap: 12 }}>
        {data.feed.map((a) => {
          const color = SPORT_COLOR[a.sport] ?? SPORT_COLOR.other;
          return (
            <div className="activity" key={a.id}>
              <div className="icon" style={{ background: `${color}1a` }}>{SPORT_EMOJI[a.sport]}</div>
              <div style={{ flex: 1 }}>
                <div className="name">{a.name}</div>
                <div className="when">
                  {fmtDate(a.date, { weekday: "long", month: "long", day: "numeric", year: "numeric" })} at {a.start_time.slice(0, 5)}
                </div>
                <div className="stats">
                  {a.distance_km > 0 && (
                    <div><span className="l">Distance</span><span className="v">{a.distance_km.toFixed(1)} km</span></div>
                  )}
                  <div><span className="l">Time</span><span className="v">{fmtMin(a.duration_min)}</span></div>
                  {a.pace && <div><span className="l">Pace</span><span className="v">{a.pace}</span></div>}
                  {a.speed_kmh && <div><span className="l">Speed</span><span className="v">{a.speed_kmh} km/h</span></div>}
                  {a.elevation_m > 0 && <div><span className="l">Elev</span><span className="v">{a.elevation_m} m</span></div>}
                  {a.avg_hr && <div><span className="l">Avg HR</span><span className="v">{Math.round(a.avg_hr)}</span></div>}
                  {a.avg_power && <div><span className="l">Power</span><span className="v">{Math.round(a.avg_power)} W</span></div>}
                  {a.rpe && <div><span className="l">RPE</span><span className="v">{a.rpe}</span></div>}
                  {a.tss != null && <div><span className="l">Load</span><span className="v">{Math.round(a.tss)}</span></div>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
