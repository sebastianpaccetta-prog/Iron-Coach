import raw from "@/public/data.json";

export type Sport = "swim" | "bike" | "run" | "strength" | "other" | "rest" | "race";

export interface Workout {
  date: string;
  weekday: string;
  sport: Sport;
  role: string;
  title: string;
  duration_min: number;
  intensity: string;
  description: string;
  emoji: string;
  completed?: boolean;
  actual_min?: number;
}

export interface WeekEval {
  week_start: string;
  phase: string;
  planned_sessions: number;
  completed_sessions: number;
  completion: number | null;
  planned_hours: number;
  actual_hours: number;
  workouts: Workout[];
}

export interface TimelineWeek {
  week_start: string;
  phase: string;
  is_recovery: boolean;
  target_hours: number;
  weeks_to_race: number;
}

export interface Activity {
  id: number;
  date: string;
  start_time: string;
  sport: Sport;
  name: string;
  duration_min: number;
  distance: number;
  elevation_m: number;
  avg_hr: number | null;
  max_hr: number | null;
  avg_power: number | null;
  pace: string | null;
  speed: number | null;
  rpe: number | null;
  tss: number | null;
}

export interface WeeklyBucket {
  week_start: string;
  total_hours: number;
  total_tss: number;
  sessions: number;
  by_sport: Record<string, { hours: number; dist: number; tss: number; sessions: number }>;
}

export interface SiteData {
  generated_at: string;
  athlete: string;
  units: { dist: string; speed: string };
  race: { name: string; date: string; days_to_race: number };
  zones: any;
  this_week: {
    week_start: string;
    week_end: string;
    phase: string;
    is_recovery: boolean;
    weeks_to_race: number;
    target_hours: number;
    planned_hours: number;
    focus: string;
    reasons: string[];
    workouts: Workout[];
    evaluation: WeekEval | null;
  };
  last_week: WeekEval | null;
  timeline: TimelineWeek[];
  feed: Activity[];
  weekly: WeeklyBucket[];
  load: { date: string; tss: number; ctl: number; atl: number; tsb: number }[];
  recovery: { date: string; resting_hr?: number; hrv?: number; sleep_hours?: number; vo2max?: number }[];
  recovery_status: { flag: string; reasons: string[]; hrv_7d: number | null; resting_hr_7d: number | null; sleep_7d: number | null; vo2max: number | null };
  fitness: { ctl: number; atl: number; tsb: number; ctl_4w_ago: number | null };
}

export const data = raw as unknown as SiteData;

export const SPORT_COLOR: Record<string, string> = {
  swim: "#0284C7",
  bike: "#F26522",
  run: "#7C3AED",
  strength: "#059669",
  other: "#6B7280",
};

export const SPORT_EMOJI: Record<string, string> = {
  swim: "🏊", bike: "🚴", run: "🏃", strength: "💪", other: "🚶", rest: "😴", race: "🏁",
};

export const SPORT_LABEL: Record<string, string> = {
  swim: "Swim", bike: "Bike", run: "Run", strength: "Strength", other: "Other", rest: "Rest", race: "Race",
};

export function fmtDate(iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "short", month: "short", day: "numeric" }) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", opts);
}

export function fmtHours(h: number) {
  const hh = Math.floor(h);
  const mm = Math.round((h - hh) * 60);
  return hh ? `${hh}h ${mm.toString().padStart(2, "0")}m` : `${mm}m`;
}

export function fmtMin(min: number) {
  return fmtHours(min / 60);
}

export const daysToRace = () => {
  const [y, m, d] = data.race.date.split("-").map(Number);
  const race = new Date(y, m - 1, d);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((race.getTime() - today.getTime()) / 86400000);
};
