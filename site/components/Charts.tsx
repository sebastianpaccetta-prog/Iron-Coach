"use client";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine,
} from "recharts";
import { data, fmtDate, SPORT_COLOR, SPORT_LABEL, fmtHours } from "@/lib/data";

const SPORTS = ["swim", "bike", "run", "strength", "other"] as const;
const AXIS = { fontSize: 12, fill: "#8a8a94", fontFamily: "var(--font-archivo)" };
const GRID = "#ececf0";

const tipStyle = { borderRadius: 4, border: "1px solid #dfdfe8", boxShadow: "0 4px 16px rgba(0,0,0,.08)", fontSize: 13 };
const LEGEND = { fontSize: 13, color: "#6d6d78" };

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
  const rows = data.recovery
    .filter((r) => r[metric] != null)
    .map((r) => ({ label: fmtDate(r.date, { month: "short", day: "numeric" }), v: Math.round((r[metric] as number) * 10) / 10 }));
  if (rows.length < 2) return <p className="fine">Not enough data yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={rows} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} minTickGap={40} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
        <Tooltip contentStyle={tipStyle} formatter={(v: number) => [`${v} ${unit}`, ""]} />
        <Line isAnimationActive={false} type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: color }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function PlannedVsActualChart() {
  const done = data.weekly.slice(-8).map((w) => ({ week: fmtDate(w.week_start, { month: "short", day: "numeric" }), actual: w.total_hours, target: null as number | null }));
  const future = data.timeline.slice(0, 8).map((t) => ({ week: fmtDate(t.week_start, { month: "short", day: "numeric" }), actual: null as number | null, target: t.target_hours }));
  const rows = [...done, ...future];
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: -18, bottom: 0 }} barCategoryGap="25%">
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="week" tick={AXIS} tickLine={false} axisLine={false} interval={1} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} unit="h" />
        <Tooltip contentStyle={tipStyle} formatter={(v: number) => fmtHours(v)} cursor={{ fill: "#f4f4f6" }} />
        <Legend iconType="square" iconSize={10} wrapperStyle={LEGEND} />
        <Bar isAnimationActive={false} dataKey="actual" name="Completed" fill="#FC5200" radius={[2, 2, 0, 0]} />
        <Bar isAnimationActive={false} dataKey="target" name="Planned" fill="#FED3BD" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
