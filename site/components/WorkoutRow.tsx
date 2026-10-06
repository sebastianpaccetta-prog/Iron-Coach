import SportIcon from "./SportIcon";
import { SPORT_COLOR, Workout, fmtDate, fmtMin } from "@/lib/data";

export default function WorkoutRow({ w, showCheck = true }: { w: Workout; showCheck?: boolean }) {
  const rest = w.sport === "rest";
  const color = SPORT_COLOR[w.sport] ?? SPORT_COLOR.other;
  const cls = ["workout", w.completed ? "done" : "", rest ? "rest" : ""].join(" ");
  return (
    <div className={cls}>
      <div className="day">
        <b>{w.weekday.slice(0, 3)}</b>
        <span>{fmtDate(w.date, { month: "short", day: "numeric" })}</span>
      </div>
      <div className="sport" style={{ color: rest ? undefined : color }}>
        <SportIcon sport={w.sport} />
      </div>
      <div className="body">
        <div className="title">{w.title}</div>
        {!rest && (
          <div className="meta">
            <b>{fmtMin(w.duration_min)}</b> · {w.intensity}
            {w.completed && w.actual_min ? <> · <span className="did">did {fmtMin(w.actual_min)}</span></> : null}
          </div>
        )}
        <p className="desc">{w.description}</p>
      </div>
      {showCheck && !rest ? (
        <div className="check" aria-label={w.completed ? "completed" : "not completed"}>
          {w.completed && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
          )}
        </div>
      ) : <div />}
    </div>
  );
}
