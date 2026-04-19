"use client";

/**
 * /sites/[key] — drill-down detail on the v2 focus shell.
 */

import { useParams } from "next/navigation";

import { FocusShell } from "@/components/dashboard-v2/shell";
import { SiteDetailView } from "@/components/sites/site-detail-view";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { useSiteDetail } from "@/hooks/use-site-detail";

export default function SiteDetailPage() {
  const params = useParams<{ key: string }>();
  const siteKey = parseInt(params.key, 10);
  const { data, isLoading, error } = useSiteDetail(
    isNaN(siteKey) ? null : siteKey,
  );

  const breadcrumbs: Array<{ label: string; href?: string }> = [
    { label: "DataPulse", href: "/dashboard" },
    { label: "Sites", href: "/sites" },
    { label: data?.site_name ?? String(siteKey) },
  ];

  const shell = (body: React.ReactNode) => (
    <FocusShell backHref="/sites" backLabel="Sites" breadcrumbs={breadcrumbs}>
      {body}
    </FocusShell>
  );

  if (isNaN(siteKey)) {
    return shell(<EmptyState title="Invalid site key" />);
  }

  if (isLoading) {
    return shell(<LoadingCard lines={10} className="h-96" />);
  }

  if (error || !data) {
    return shell(<EmptyState title="Site not found" />);
  }

  return shell(
    <>
      <div>
        <h1 className="page-title">{data.site_name}</h1>
        {data.area_manager && (
          <p className="page-sub">Area Manager: {data.area_manager}</p>
        )}
      </div>

      <SiteDetailView site={data} />
    </>,
  );
}
