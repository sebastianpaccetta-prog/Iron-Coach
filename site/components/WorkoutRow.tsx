import { Workout, fmtDate, fmtMin } from "@/lib/data";

export default function WorkoutRow({ w, showCheck = true }: { w: Workout; showCheck?: boolean }) {
  const rest = w.sport === "rest";
  const cls = ["workout", w.completed ? "done" : "", rest ? "rest" : ""].join(" ");
  return (
    <div className={cls}>
      <div className="day">
        {w.weekday.slice(0, 3)}
        <span>{fmtDate(w.date, { month: "short", day: "numeric" })}</span>
      </div>
      <div className="emoji">{w.emoji}</div>
      <div>
        <div className="title">{w.title}</div>
        {!rest && (
          <div className="meta">
            {fmtMin(w.duration_min)} · {w.intensity}
            {w.completed && w.actual_min ? ` · done: ${fmtMin(w.actual_min)}` : ""}
          </div>
        )}
        <div className="desc">{w.description}</div>
      </div>
      {showCheck && !rest ? <div className="check">{w.completed ? "✓" : ""}</div> : <div />}
    </div>
  );
}
