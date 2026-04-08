"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { BrandSettings } from "@/components/branding/brand-settings";

export default function BrandingPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Branding & White-Label"
        description="Customize your organization's branding, colors, and domain"
      />
      <BrandSettings />
    </PageTransition>
  );
}
