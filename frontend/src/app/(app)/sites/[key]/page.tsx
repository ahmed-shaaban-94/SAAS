"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, MapPin } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { SiteDetailView } from "@/components/sites/site-detail-view";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { useSiteDetail } from "@/hooks/use-site-detail";

export default function SiteDetailPage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = use(params);
  const siteKey = parseInt(key, 10);
  const { data, isLoading, error } = useSiteDetail(
    isNaN(siteKey) ? null : siteKey,
  );

  if (isNaN(siteKey)) {
    return (
      <PageTransition>
        <Breadcrumbs />
        <EmptyState title="Invalid site key" />
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <Breadcrumbs />
      <div className="mb-4">
        <Link
          href="/sites"
          className="inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-accent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Sites
        </Link>
      </div>

      {isLoading ? (
        <LoadingCard lines={10} className="h-96" />
      ) : error || !data ? (
        <EmptyState title="Site not found" />
      ) : (
        <>
          <Header
            title={data.site_name}
            description={
              data.area_manager
                ? `Area Manager: ${data.area_manager}`
                : undefined
            }
          />
          <SiteDetailView site={data} />
        </>
      )}
    </PageTransition>
  );
}
