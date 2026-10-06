import { ReactNode } from "react";

export interface Stat {
  label: string;
  value: ReactNode;
  unit?: string;
  sub?: ReactNode;
  accent?: boolean;
}

// Strava-style numbers: small label on top, big condensed figure, hairline dividers.
export default function StatRow({ stats, size = "lg" }: { stats: Stat[]; size?: "lg" | "sm" }) {
  return (
    <dl className={`stat-row ${size}`}>
      {stats.map((s) => (
        <div key={s.label} className={s.accent ? "accent" : ""}>
          <dt>{s.label}</dt>
          <dd>
            <span className="num">{s.value}</span>
            {s.unit && <span className="unit">{s.unit}</span>}
          </dd>
          {s.sub && <p className="sub">{s.sub}</p>}
        </div>
      ))}
    </dl>
  );
}
