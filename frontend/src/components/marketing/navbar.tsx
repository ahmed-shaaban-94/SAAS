"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Activity, Menu, X } from "lucide-react";
import { NAV_LINKS } from "@/lib/marketing-constants";

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
          ? "border-b border-border bg-page/80 backdrop-blur-md"
          : "bg-transparent"
      }`}
    >
      <nav
        className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <Activity className="h-7 w-7 text-accent" />
          <span className="text-xl font-bold text-accent">DataPulse</span>
        </Link>

        {/* Desktop links */}
        <div className="hidden items-center gap-8 lg:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-text-secondary transition-colors hover:text-text-primary"
            >
              {link.label}
            </a>
          ))}
          <Link
            href="/dashboard"
            className="rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-page shadow-[0_0_15px_rgba(255,69,0,0.4)] transition-all hover:bg-accent/90 hover:shadow-[0_0_20px_rgba(255,69,0,0.6)]"
          >
            Get Started
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="rounded-lg p-2 text-text-secondary hover:text-text-primary lg:hidden"
          aria-label={isMobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={isMobileOpen}
        >
          {isMobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </nav>

      {/* Mobile menu */}
      {isMobileOpen && (
        <div className="border-t border-border bg-page/95 backdrop-blur-md lg:hidden">
          <div className="mx-auto max-w-6xl space-y-1 px-4 py-4 sm:px-6">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setIsMobileOpen(false)}
                className="block rounded-lg px-4 py-3 text-sm font-medium text-text-secondary transition-colors hover:bg-card hover:text-text-primary"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="/dashboard"
              onClick={() => setIsMobileOpen(false)}
              className="mt-2 block rounded-lg bg-accent px-4 py-3 text-center text-sm font-semibold text-page transition-colors hover:bg-accent/90"
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
