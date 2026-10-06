"use client";
import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine,
} from "recharts";
import { data, fmtDate, SPORT_COLOR, SPORT_LABEL, fmtHours } from "@/lib/data";

const SPORTS = ["swim", "bike", "run", "strength", "other"] as const;
const AXIS = { fontSize: 12, fill: "#8a8a94", fontFamily: "var(--font-archivo)" };
const GRID = "#ececf0";

const tipStyle = { borderRadius: 4, border: "1px solid #dfdfe8", boxShadow: "0 4px 16px rgba(0,0,0,.08)", fontSize: 13 };
const LEGEND = { fontSize: 13, color: "#6d6d78" };

const DAY_MS = 86_400_000;
const round1 = (n: number) => Math.round(n * 10) / 10;

// Least-squares line through (date, value) points, x measured in days so uneven gaps are weighted correctly.
// Returns a function giving the fitted value at a date, or null if there are too few points to fit.
function trendFn(points: { date: string; v: number }[]): ((date: string) => number) | null {
  if (points.length < 2) return null;
  const xs = points.map((p) => Date.parse(p.date) / DAY_MS);
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = points.reduce((a, p) => a + p.v, 0) / n;
  let sxy = 0, sxx = 0;
  xs.forEach((x, i) => { sxy += (x - mx) * (points[i].v - my); sxx += (x - mx) ** 2; });
  if (sxx === 0) return null;
  const slope = sxy / sxx;
  return (date) => round1(my + slope * (Date.parse(date) / DAY_MS - mx));
}

export function WeeklyVolumeChart() {
  const rows = data.weekly.map((w) => ({
    week: fmtDate(w.week_start, { month: "short", day: "numeric" }),
    swim: w.by_sport.swim.hours,
    bike: w.by_sport.bike.hours,
    run: w.by_sport.run.hours,
    strength: w.by_sport.strength.hours,
    other: w.by_sport.other.hours,
    total: w.total_hours,
  }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: -18, bottom: 0 }} barCategoryGap="30%">
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="week" tick={AXIS} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} unit="h" />
        <Tooltip contentStyle={tipStyle} formatter={(v: number, n: string) => [fmtHours(v), SPORT_LABEL[n] ?? n]} cursor={{ fill: "#f4f4f6" }} />
        <Legend iconType="square" iconSize={10} wrapperStyle={LEGEND} formatter={(v) => SPORT_LABEL[v] ?? v} />
        {SPORTS.map((s, i) => (
          <Bar key={s} dataKey={s} isAnimationActive={false} stackId="a" fill={SPORT_COLOR[s]} stroke="#fff" strokeWidth={1}
               radius={i === SPORTS.length - 1 ? [2, 2, 0, 0] : 0} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LoadChart() {
  const rows = data.load.map((d) => ({ ...d, label: fmtDate(d.date, { month: "short", day: "numeric" }) }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={rows} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} minTickGap={40} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={tipStyle} />
        <Legend iconType="plainline" wrapperStyle={LEGEND} />
        <ReferenceLine y={0} stroke="#c8c8d0" />
        <Line isAnimationActive={false} type="monotone" dataKey="ctl" name="Fitness (CTL)" stroke="#FC5200" strokeWidth={2.5} dot={false} />
        <Line isAnimationActive={false} type="monotone" dataKey="atl" name="Fatigue (ATL)" stroke="#242428" strokeWidth={1.5} dot={false} />
        <Line isAnimationActive={false} type="monotone" dataKey="tsb" name="Form (TSB)" stroke="#2F7EC1" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function RecoveryChart({ metric, color, unit }: { metric: "hrv" | "resting_hr" | "sleep_hours"; color: string; unit: string }) {
  const pts = data.recovery
    .filter((r) => r[metric] != null)
    .map((r) => ({ date: r.date, v: round1(r[metric] as number) }));
  if (pts.length < 2) return <p className="fine">Not enough data yet.</p>;
  const fit = trendFn(pts);
  const rows = pts.map((p) => ({ label: fmtDate(p.date, { month: "short", day: "numeric" }), v: p.v, trend: fit ? fit(p.date) : null }));
  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={rows} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} minTickGap={40} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
        <Tooltip contentStyle={tipStyle} formatter={(v: number, n: string) => [`${v} ${unit}`, n === "trend" ? "Trend" : ""]} />
        <Line isAnimationActive={false} type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: color }} />
        <Line isAnimationActive={false} type="linear" dataKey="trend" stroke="#242428" strokeWidth={1.5} strokeDasharray="5 4" dot={false} activeDot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function PlannedVsActualChart() {
  const done = data.weekly.slice(-8).map((w) => ({ date: w.week_start, actual: w.total_hours as number | null, target: null as number | null }));
  const future = data.timeline.slice(0, 8).map((t) => ({ date: t.week_start, actual: null as number | null, target: t.target_hours as number | null }));
  const all = [...done, ...future];
  const fitDone = trendFn(done.map((r) => ({ date: r.date, v: r.actual as number })));
  const fitPlan = trendFn(future.map((r) => ({ date: r.date, v: r.target as number })));
  const rows = all.map((r) => ({
    ...r,
    week: fmtDate(r.date, { month: "short", day: "numeric" }),
    actualTrend: fitDone && r.actual != null ? fitDone(r.date) : null,
    targetTrend: fitPlan && r.target != null ? fitPlan(r.date) : null,
  }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, left: -18, bottom: 0 }} barCategoryGap="25%">
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="week" tick={AXIS} tickLine={false} axisLine={false} interval={1} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} unit="h" />
        <Tooltip contentStyle={tipStyle} formatter={(v: number) => fmtHours(v)} cursor={{ fill: "#f4f4f6" }} />
        <Legend iconType="square" iconSize={10} wrapperStyle={LEGEND} />
        <Bar isAnimationActive={false} dataKey="actual" name="Completed" fill="#FC5200" radius={[2, 2, 0, 0]} />
        <Bar isAnimationActive={false} dataKey="target" name="Planned" fill="#FED3BD" radius={[2, 2, 0, 0]} />
        <Line isAnimationActive={false} type="linear" dataKey="actualTrend" name="Completed trend" stroke="#242428" strokeWidth={1.5} strokeDasharray="5 4" dot={false} activeDot={false} legendType="plainline" />
        <Line isAnimationActive={false} type="linear" dataKey="targetTrend" name="Planned trend" stroke="#E07A45" strokeWidth={1.5} strokeDasharray="5 4" dot={false} activeDot={false} legendType="plainline" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
