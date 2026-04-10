import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Live Demo | DataPulse",
  description:
    "Try DataPulse with simulated real-time sales data — no sign-in required.",
};

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen" style={{ background: "#0D1117", color: "#E6EDF3" }}>
      {/* Minimal demo banner */}
      <header
        className="flex items-center justify-between border-b px-4 py-2.5"
        style={{ borderColor: "#21262D" }}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold tracking-tight" style={{ color: "#6366F1" }}>
            DataPulse
          </span>
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
            style={{ background: "#6366F115", color: "#6366F1" }}
          >
            Demo
          </span>
        </div>
        <Link
          href="/login"
          className="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors"
          style={{ background: "#6366F1", color: "#fff" }}
        >
          Sign In
        </Link>
      </header>
      <main>{children}</main>
    </div>
  );
}
