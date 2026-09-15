"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Logo from "./Logo";

const LINKS = [
  { href: "/", label: "This week" },
  { href: "/feed", label: "Activity feed" },
  { href: "/progress", label: "Progress" },
  { href: "/plan", label: "Plan overview" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="nav">
      <div className="nav-inner">
        <Link href="/" className="brand">
          <Logo /> Iron Coach
        </Link>
        <div className="nav-links">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className={path === l.href ? "active" : ""}>
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
