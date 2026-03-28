import Link from "next/link";
import { Activity } from "lucide-react";
import { FOOTER_COLUMNS, SITE_NAME } from "@/lib/marketing-constants";

export function Footer() {
  return (
    <footer className="border-t border-border bg-card/50">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {FOOTER_COLUMNS.map((column) => (
            <div key={column.title}>
              <h3 className="text-sm font-semibold text-text-primary">
                {column.title}
              </h3>
              <ul className="mt-4 space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}>
                    {link.href.startsWith("#") || link.href.startsWith("/") ? (
                      <Link
                        href={link.href}
                        className="text-sm text-text-secondary transition-colors hover:text-accent"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <a
                        href={link.href}
                        className="text-sm text-text-secondary transition-colors hover:text-accent"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Copyright */}
        <div className="mt-12 flex flex-col items-center gap-4 border-t border-border pt-8 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-accent" />
            <span className="text-sm font-semibold text-accent">{SITE_NAME}</span>
          </div>
          <p className="text-sm text-text-secondary">
            &copy; {new Date().getFullYear()} {SITE_NAME}. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
