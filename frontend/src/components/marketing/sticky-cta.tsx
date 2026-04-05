"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function StickyCTA() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      // Show after scrolling past the hero section (~600px)
      setShow(window.scrollY > 600);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-40 p-4 transition-transform duration-400 ${
        show ? "translate-y-0" : "translate-y-[150%]"
      }`}
    >
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 rounded-2xl border border-border/40 bg-card/80 p-4 shadow-2xl backdrop-blur-xl">
        <div className="hidden sm:block">
          <h4 className="text-sm font-bold text-text-primary">
            Ready to turn your data into insights?
          </h4>
          <p className="text-xs text-text-secondary">
            Free during beta. No credit card required.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="cta-shimmer whitespace-nowrap rounded-xl bg-accent px-6 py-2.5 text-sm font-bold text-page transition-colors hover:bg-accent/90"
        >
          Start Free Trial
        </Link>
      </div>
    </div>
  );
}
