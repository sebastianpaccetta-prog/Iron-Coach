import Link from "next/link";
import Countdown from "@/components/Countdown";
import Logo from "@/components/Logo";
import Photo from "@/components/Photo";
import StatRow from "@/components/StatRow";
import { data, fmtDate, fmtHours } from "@/lib/data";
import bikeImg from "@/public/images/bike.jpg";
import finishImg from "@/public/images/finish.jpg";
import heroImg from "@/public/images/hero.jpg";
import swimImg from "@/public/images/swim.jpg";
import runImg from "@/public/images/run.jpg";

const FEATURES = [
  {
    img: swimImg,
    pos: "center 40%",
    alt: "",
    kicker: "01 · Your data",
    title: "Bring your Strava. That's the setup.",
    body: "Export your Strava archive, drop the folder in, and Iron Coach reads every swim, ride and run you've logged. Add an Apple Health export and it also watches your HRV, resting heart rate and sleep.",
  },
  {
    img: bikeImg,
    pos: "center",
    alt: "",
    kicker: "02 · The plan",
    title: "Next week is built from the week you actually had.",
    body: "Every Sunday it scores your training load, tracks fitness and fatigue, and writes the next seven days. Missed a long ride? Slept badly? The plan adjusts instead of pretending it didn't happen.",
  },
  {
    img: runImg,
    pos: "50% 30%",
    alt: "",
    kicker: "03 · Your calendar",
    title: "Every workout lands in your calendar.",
    body: "Sessions go straight to a dedicated Google Calendar with the full set, the target zone and the reason it's there. Open it at the pool or on the trainer and just do the work.",
  },
];

const PRINCIPLES = [
  { h: "Load, not guesswork", p: "Each session gets a training-stress score. Fitness (42-day) and fatigue (7-day) averages decide how hard the next week can be." },
  { h: "Built in phases", p: "Base, build, peak, taper. Volume ramps at most 10% a week, with a lighter week every fourth to absorb the work." },
  { h: "Your zones", p: "Heart-rate and pace zones come from your own history, and you can pin tested values once you have them." },
];

export default function Landing() {
  const totalHours = data.weekly.reduce((s, w) => s + w.total_hours, 0);
  const race = fmtDate(data.race.date, { month: "long", day: "numeric", year: "numeric" });

  return (
    <div className="landing">
      <header className="l-header">
        <Link href="/" aria-label="Iron Coach home"><Logo light /></Link>
        <nav>
          <a href="#how">How it works</a>
          <Link href="/week" className="btn btn-sm">Open dashboard</Link>
        </nav>
      </header>

      <section className="l-hero photo">
        <Photo src={heroImg} position="center 40%" priority alt="Triathletes running into the sea at a race start" />
        <div className="l-hero-inner">
          <h1>Train for your 70.3 like you have a coach.</h1>
          <p>
            Iron Coach reads your Strava every Sunday, works out what you can handle, and puts next week's swims,
            rides and runs in your calendar.
          </p>
          <div className="l-ctas">
            <Link href="/week" className="btn">See the dashboard</Link>
            <a href="#how" className="btn btn-ghost">How it works</a>
          </div>
        </div>
        <div className="l-hero-count">
          <Countdown label={`days to ${data.race.name}`} />
        </div>
      </section>

      <section id="how" className="l-features">
        {FEATURES.map((f, i) => (
          <div key={f.title} className={`l-feature${i % 2 ? " flip" : ""}`}>
            <div className="l-feature-img photo">
              <Photo src={f.img} position={f.pos} sizes="(max-width: 820px) 100vw, 600px" alt={f.alt} />
            </div>
            <div className="l-feature-text">
              <span className="kicker">{f.kicker}</span>
              <h2>{f.title}</h2>
              <p>{f.body}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="l-live">
        <div className="l-wrap">
          <span className="kicker">Live from this season</span>
          <h2>One athlete, {data.weekly.length} weeks of data, {race} on the calendar.</h2>
          <StatRow
            stats={[
              { label: "Hours logged", value: Math.round(totalHours), unit: "h" },
              { label: "Activities in feed", value: data.feed.length },
              { label: "This week", value: fmtHours(data.this_week.planned_hours), sub: `${data.this_week.phase[0].toUpperCase() + data.this_week.phase.slice(1)} phase` },
              { label: "Fitness", value: Math.round(data.fitness.ctl), sub: "CTL", accent: true },
            ]}
          />
        </div>
      </section>

      <section className="l-principles l-wrap">
        <span className="kicker">The coaching</span>
        <h2>Real training science, explained in plain words.</h2>
        <div className="l-cols">
          {PRINCIPLES.map((x) => (
            <div key={x.h}>
              <h3>{x.h}</h3>
              <p>{x.p}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="l-close photo">
        <Photo src={finishImg} position="center 30%" alt="Athlete crossing a finish line holding the tape" />
        <div className="l-wrap">
          <h2>Race day is {race}.<br />Start this Sunday.</h2>
          <Link href="/update" className="btn">Set it up</Link>
        </div>
      </section>

      <footer className="l-footer l-wrap">
        <Logo />
        <span>Built for one race, open to anyone training for theirs.</span>
      </footer>
    </div>
  );
}
