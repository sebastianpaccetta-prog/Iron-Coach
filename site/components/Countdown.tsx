"use client";
import { useEffect, useState } from "react";
import { data, daysToRace } from "@/lib/data";

export default function Countdown() {
  // Rendered from the build-time value first, then corrected in the browser so
  // the number stays right even if the site was not redeployed today.
  const [days, setDays] = useState(data.race.days_to_race);
  useEffect(() => setDays(daysToRace()), []);
  return (
    <span className="big">
      {days}
      <small>days to race</small>
    </span>
  );
}
