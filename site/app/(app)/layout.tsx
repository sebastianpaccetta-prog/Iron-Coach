import Nav from "@/components/Nav";
import { data } from "@/lib/data";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <Nav />
      <main className="container">{children}</main>
      <footer className="app-footer">
        Data updated {new Date(data.generated_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
      </footer>
    </div>
  );
}
