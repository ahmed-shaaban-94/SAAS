"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

const pathLabels: Record<string, string> = {
  dashboard: "Overview",
  products: "Products",
  customers: "Customers",
  staff: "Staff",
  sites: "Sites",
  returns: "Returns",
  pipeline: "Pipeline",
  insights: "Insights",
};

interface Crumb {
  label: string;
  href: string;
}

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) return null;

  const crumbs: Crumb[] = [{ label: "Home", href: "/dashboard" }];

  segments.forEach((segment, index) => {
    const href = "/" + segments.slice(0, index + 1).join("/");
    const label =
      pathLabels[segment] ??
      (index > 0 ? "Detail" : segment.charAt(0).toUpperCase() + segment.slice(1));

    // Skip if this crumb's href matches the Home crumb (avoids duplicate key on /dashboard)
    if (href === "/dashboard") return;

    // For dynamic segments after a known parent, use "Parent > ... Detail"
    if (index > 0 && !pathLabels[segment]) {
      const parentLabel = pathLabels[segments[index - 1]];
      if (parentLabel) {
        // Proper singularization (avoids "Staff" → "Staf")
        const singular =
          parentLabel.endsWith("ies")
            ? parentLabel.slice(0, -3) + "y"
            : parentLabel.endsWith("s") && !parentLabel.endsWith("ss")
              ? parentLabel.slice(0, -1)
              : parentLabel;
        crumbs.push({
          label: `${singular} Detail`,
          href,
        });
        return;
      }
    }

    crumbs.push({ label, href });
  });

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs">
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1;

        return (
          <span key={crumb.href} className="flex items-center gap-1">
            {index > 0 && (
              <ChevronRight className="h-3 w-3 text-text-secondary" />
            )}
            {isLast ? (
              <span className="font-medium text-accent">{crumb.label}</span>
            ) : (
              <Link
                href={crumb.href}
                className="text-text-secondary transition-colors hover:text-text-primary"
              >
                {crumb.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
