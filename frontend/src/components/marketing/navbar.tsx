"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Activity, Menu, X } from "lucide-react";
import { NAV_LINKS } from "@/lib/marketing-constants";
import { PulseLine } from "./pulse-line";

export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (isMobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobileOpen]);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? "border-b border-white/10 bg-[#081826]/75 backdrop-blur-xl"
          : "bg-transparent"
      }`}
    >
      <nav
        className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
        aria-label="Main navigation"
      >
        {/* Logo with ECG pulse line */}
        <Link href="/" className="flex flex-col">
          <div className="flex items-center gap-2">
            <Activity className="h-7 w-7 text-accent" />
            <span className="text-xl font-bold tracking-tight text-text-primary">Data Pulse</span>
          </div>
          <PulseLine />
        </Link>

        {/* Desktop links */}
        <div className="hidden items-center gap-8 lg:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-full px-3 py-2 text-sm font-medium text-text-secondary transition-colors hover:bg-white/5 hover:text-text-primary"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Desktop CTAs */}
        <div className="hidden items-center gap-3 lg:flex">
          <Link
            href="/demo"
            className="rounded-full border border-white/15 bg-white/5 px-5 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-white/10"
          >
            See Demo
          </Link>
          <Link
            href="#pilot-access"
            className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-page shadow-[0_0_16px_rgba(0,199,242,0.3)] transition-all hover:shadow-[0_0_24px_rgba(0,199,242,0.45)]"
          >
            Request Pilot Access
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="rounded-xl border border-white/10 bg-white/5 p-2 text-text-secondary hover:text-text-primary lg:hidden"
          aria-label={isMobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={isMobileOpen}
        >
          {isMobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </nav>

      {/* Mobile menu */}
      {isMobileOpen && (
        <div className="border-t border-white/10 bg-[#081826]/95 backdrop-blur-xl lg:hidden">
          <div className="mx-auto max-w-6xl space-y-1 px-4 py-4 sm:px-6">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setIsMobileOpen(false)}
                className="block rounded-xl px-4 py-3 text-sm font-medium text-text-secondary transition-colors hover:bg-white/5 hover:text-text-primary"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="#pilot-access"
              onClick={() => setIsMobileOpen(false)}
              className="block rounded-full bg-accent px-5 py-2.5 text-center text-sm font-semibold text-page"
            >
              Request Pilot Access
            </Link>
            <Link
              href="/demo"
              onClick={() => setIsMobileOpen(false)}
              className="block rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-center text-sm font-medium text-text-primary"
            >
              See Demo
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
