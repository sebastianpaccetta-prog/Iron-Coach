import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { data } from "@/lib/data";

export const metadata: Metadata = {
  title: "Iron Coach",
  description: "Personal 70.3 training dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="container">{children}</main>
        <p className="footer">Data updated {new Date(data.generated_at).toLocaleString("en-US")} · Iron Coach</p>
      </body>
    </html>
  );
}
