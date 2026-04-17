# Phase 1 — Market Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the DataPulse marketing landing page from generic analytics messaging to pharma-first positioning, with honest CTAs and no unsupported trust claims.

**Architecture:** All landing page content is data-driven via `frontend/src/lib/marketing-constants.ts`. Most changes happen there. Three components need structural changes (not just data): `trust-bar.tsx` (replace scrolling logos with text list), `stats-banner.tsx` (replace animated numeric counters with qualitative claims grid), and `navbar.tsx` (add dual CTA buttons). The existing `marketing.spec.ts` Playwright tests are updated first (TDD) and will drive verification.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, Playwright (E2E tests), Vitest (unit tests)

---

## File Map

| Action | File |
|--------|------|
| Modify | `frontend/e2e/marketing.spec.ts` — update tests to match new content (do this first) |
| Modify | `frontend/src/lib/marketing-constants.ts` — all content arrays |
| Modify | `frontend/src/components/marketing/hero-section.tsx` — eyebrow, headline, KPI strip, CTAs |
| Modify | `frontend/src/components/marketing/trust-bar.tsx` — replace scrolling logos |
| Modify | `frontend/src/components/marketing/stats-banner.tsx` — replace animated counters |
| Modify | `frontend/src/components/marketing/cta-section.tsx` — new copy + Phase 4 marker |
| Modify | `frontend/src/components/marketing/navbar.tsx` — add dual CTA buttons |
| Modify | `frontend/src/app/(marketing)/page.tsx` — metadata, remove TechBadges, Phase 4 marker |

---

## Task 1: Update E2E Tests (TDD — write failing tests first)

**Files:**
- Modify: `frontend/e2e/marketing.spec.ts`

- [ ] **Step 1: Replace marketing.spec.ts with pharma-first tests**

Open `frontend/e2e/marketing.spec.ts` and replace the entire file content with:

```typescript
import { test, expect } from "@playwright/test";

test.describe("Marketing Landing Page — Pharma-First", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  // ── Hero ──────────────────────────────────────────────────────────────────

  test("hero headline is pharma-first", async ({ page }) => {
    await expect(page.locator("h1")).toContainText(
      "Turn pharma sales and operations data into daily decisions",
      { timeout: 15000 }
    );
  });

  test("primary CTA reads Request Pilot Access", async ({ page }) => {
    const ctas = page.getByRole("link", { name: /Request Pilot Access/i });
    await expect(ctas.first()).toBeVisible();
  });

  test("no generic Get Started or Join Beta CTAs exist", async ({ page }) => {
    await expect(page.getByText(/Get Started Free/i)).toHaveCount(0);
    await expect(page.getByText(/Join Beta/i)).toHaveCount(0);
    await expect(page.getByText(/Start Free Trial/i)).toHaveCount(0);
  });

  // ── Trust bar ─────────────────────────────────────────────────────────────

  test("no placeholder trust claims", async ({ page }) => {
    // Old: "Trusted by 500+ data teams worldwide"
    await expect(page.getByText(/Trusted by/i)).toHaveCount(0);
    // Old placeholder company names
    await expect(page.getByText("Pharma Corp")).toHaveCount(0);
    await expect(page.getByText("RetailMax")).toHaveCount(0);
  });

  test("trust bar shows pharma use-case list", async ({ page }) => {
    await expect(
      page.getByText(/branch performance/i)
    ).toBeVisible();
  });

  // ── Navigation ────────────────────────────────────────────────────────────

  test("navbar has Pilot Access link", async ({ page }) => {
    await expect(
      page.locator("nav").getByRole("link", { name: /Pilot Access/i }).first()
    ).toBeVisible();
  });

  test("navbar has See Demo secondary CTA", async ({ page }) => {
    await expect(
      page.locator("header").getByRole("link", { name: /See Demo/i })
    ).toBeVisible();
  });

  test("no Features nav link (renamed to Product or Use Cases)", async ({ page }) => {
    // Old nav had "Features" as a link — new nav has "Product" and "Use Cases"
    const featureNavLink = page.locator('nav a[href="#features"]');
    await expect(featureNavLink).toHaveCount(0);
  });

  // ── How It Works ──────────────────────────────────────────────────────────

  test("how it works shows pharma operational steps", async ({ page }) => {
    const section = page.locator("#how-it-works");
    await expect(section).toBeVisible();
    await expect(section.getByText(/Import your data/i).first()).toBeVisible();
    await expect(section.getByText(/Clean and validate/i).first()).toBeVisible();
    await expect(section.getByText(/See the business clearly/i).first()).toBeVisible();
    await expect(section.getByText(/Act faster/i).first()).toBeVisible();
  });

  // ── Features ──────────────────────────────────────────────────────────────

  test("features section shows pharma-specific capabilities", async ({ page }) => {
    const section = page.locator("#features");
    await expect(section).toBeVisible();
    await expect(section.getByText(/Inventory And Expiry/i).first()).toBeVisible();
  });

  // ── Stats ─────────────────────────────────────────────────────────────────

  test("no numeric vanity stats", async ({ page }) => {
    // Old: "2.2M+ Rows Processed", "10x Faster than Pandas", "25+ API Endpoints"
    await expect(page.getByText(/10x/i)).toHaveCount(0);
    await expect(page.getByText(/Faster than Pandas/i)).toHaveCount(0);
    await expect(page.getByText(/API Endpoints/i)).toHaveCount(0);
  });

  test("qualitative claims section is visible", async ({ page }) => {
    await expect(
      page.getByText(/Reporting cycles/i).first()
    ).toBeVisible();
  });

  // ── Pilot Access (formerly Pricing) ───────────────────────────────────────

  test("section is Pilot Access not Pricing", async ({ page }) => {
    await expect(page.locator("#pilot-access")).toBeVisible();
    await expect(page.locator("#pricing")).toHaveCount(0);
  });

  test("pilot tiers use correct names", async ({ page }) => {
    const section = page.locator("#pilot-access");
    await expect(section.getByText("Explorer Pilot")).toBeVisible();
    await expect(section.getByText("Operations Pilot")).toBeVisible();
    await expect(section.getByText("Enterprise Rollout")).toBeVisible();
  });

  test("no old pricing tier names", async ({ page }) => {
    await expect(page.getByText(/^Starter$/)).toHaveCount(0);
    await expect(page.getByText(/^Pro$/)).toHaveCount(0);
  });

  // ── FAQ ───────────────────────────────────────────────────────────────────

  test("FAQ has pharma-specific questions", async ({ page }) => {
    const faqSection = page.locator("#faq");
    await expect(faqSection).toBeVisible();
    await expect(
      faqSection.getByText(/Who is DataPulse for/i)
    ).toBeVisible();
  });

  test("no technical FAQ questions", async ({ page }) => {
    await expect(
      page.getByText(/What data formats does Data Pulse support/i)
    ).toHaveCount(0);
    await expect(
      page.getByText(/How does the medallion architecture work/i)
    ).toHaveCount(0);
  });

  // ── CTA Section ───────────────────────────────────────────────────────────

  test("bottom CTA section uses pharma-first copy", async ({ page }) => {
    await expect(
      page.getByText(/See what your team should act on every day/i)
    ).toBeVisible();
  });

  test("no waitlist or launch language in CTA", async ({ page }) => {
    await expect(page.getByText(/Join the waitlist/i)).toHaveCount(0);
    await expect(page.getByText(/Launch with clarity/i)).toHaveCount(0);
  });

  // ── Static pages ─────────────────────────────────────────────────────────

  test("privacy page loads", async ({ page }) => {
    await page.goto("/privacy");
    await expect(page.locator("h1")).toContainText(/Privacy Policy/i);
  });

  test("terms page loads", async ({ page }) => {
    await page.goto("/terms");
    await expect(page.locator("h1")).toContainText(/Terms of Service/i);
  });
});
```

- [ ] **Step 2: Run the tests — verify they all fail**

```bash
cd frontend
npx playwright test e2e/marketing.spec.ts --reporter=list
```

Expected: most tests FAIL. This is correct — we haven't changed the code yet. Confirm that failures match expectations (old content exists, new content doesn't).

---

## Task 2: Update marketing-constants.ts

**Files:**
- Modify: `frontend/src/lib/marketing-constants.ts`

- [ ] **Step 1: Update SITE_NAME, SITE_DESCRIPTION, NAV_LINKS**

Open `frontend/src/lib/marketing-constants.ts`.

Replace the `SITE_NAME`, `SITE_DESCRIPTION`, and `NAV_LINKS` sections:

```typescript
export const SITE_NAME = "DataPulse";
export const SITE_DESCRIPTION =
  "DataPulse helps pharma and retail operations teams turn messy sales and inventory data into daily decision-ready intelligence.";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://smartdatapulse.tech";

export const NAV_LINKS = [
  { label: "Product",     href: "#features"    },
  { label: "How It Works",href: "#how-it-works" },
  { label: "Use Cases",   href: "#use-cases"   },
  { label: "Pilot Access",href: "#pilot-access" },
  { label: "FAQ",         href: "#faq"         },
] as const;
```

- [ ] **Step 2: Update FEATURES array**

Replace the `FEATURES` array:

```typescript
export const FEATURES: FeatureItem[] = [
  {
    icon: "FileUp",
    title: "Data Intake That Works With Real Spreadsheets",
    description:
      "Import Excel and CSV files or connect managed sources without forcing your team to clean everything manually first.",
  },
  {
    icon: "ShieldCheck",
    title: "Automated Cleaning And Validation",
    description:
      "Catch duplicates, schema issues, and broken inputs before they distort your dashboards.",
  },
  {
    icon: "BarChart3",
    title: "Executive Revenue Visibility",
    description:
      "Track revenue, trend shifts, branch performance, and product movement from one executive overview.",
  },
  {
    icon: "Package",
    title: "Inventory And Expiry Awareness",
    description:
      "Surface stock and expiry risks early so teams can respond before margin and service levels are affected.",
  },
  {
    icon: "Sparkles",
    title: "Alerts And Explainable Insights",
    description:
      "Highlight what changed, where to look next, and which problems need action now.",
  },
  {
    icon: "FileBarChart",
    title: "Operational Reporting That Travels",
    description:
      "Turn dashboards into reports, briefings, and shared outputs for leaders, branches, and partner teams.",
  },
];
```

- [ ] **Step 3: Update PIPELINE_STEPS array**

Replace `PIPELINE_STEPS` with the user-facing operational flow:

```typescript
export const PIPELINE_STEPS: PipelineStep[] = [
  {
    number: 1,
    icon: "FileUp",
    label: "Import your data",
    layer: "",
    description:
      "Bring in spreadsheets or connected sources from sales and operations workflows.",
  },
  {
    number: 2,
    icon: "ShieldCheck",
    label: "Clean and validate automatically",
    layer: "",
    description:
      "Standardize the data, catch quality issues, and make the numbers safer to trust.",
  },
  {
    number: 3,
    icon: "BarChart3",
    label: "See the business clearly",
    layer: "",
    description:
      "Track executive KPIs, branch trends, inventory signals, and operational risks from one system.",
  },
  {
    number: 4,
    icon: "Zap",
    label: "Act faster",
    layer: "",
    description:
      "Use alerts, reports, and drill-downs to move from explanation to action.",
  },
];
```

- [ ] **Step 4: Replace STATS with CLAIMS (qualitative)**

Add the new `ClaimItem` type and `CLAIMS` array. Remove `Stat` type and `STATS` array:

```typescript
export interface ClaimItem {
  icon: string;
  headline: string;
  description: string;
}

export const CLAIMS: ClaimItem[] = [
  {
    icon: "Clock",
    headline: "Reporting cycles cut from days to hours",
    description: "Weekly sales reporting that used to take days runs automatically.",
  },
  {
    icon: "Eye",
    headline: "One trusted view across commercial and operations data",
    description: "Revenue, inventory, expiry, and branch performance in a single system.",
  },
  {
    icon: "AlertTriangle",
    headline: "Early visibility into stock and expiry risk",
    description: "Catch problems before they become margin or service-level failures.",
  },
  {
    icon: "Zap",
    headline: "Faster investigation from alert to action",
    description: "From anomaly detection to fix path — without manual data digging.",
  },
];
```

- [ ] **Step 5: Replace PRICING_TIERS with pilot tiers**

Replace `PRICING_TIERS`:

```typescript
export const PRICING_TIERS: PricingTier[] = [
  {
    name: "Explorer Pilot",
    price: "Pilot",
    period: "",
    description:
      "Best for teams validating fit with a sample workflow and a limited set of branches or data sources.",
    features: [
      "Up to 3 data sources",
      "Revenue and branch dashboards",
      "Automated cleaning and validation",
      "Pipeline health monitoring",
      "Onboarding support",
    ],
    cta: "Apply for Pilot",
    isPopular: false,
  },
  {
    name: "Operations Pilot",
    price: "Pilot",
    period: "",
    description:
      "Best for teams that need revenue visibility plus inventory, expiry, and operational monitoring in one environment.",
    badge: "Most requested",
    features: [
      "Unlimited data sources",
      "Full analytics and operations suite",
      "Inventory, expiry, and PO tracking",
      "Alerts and explainable insights",
      "Reports and briefings",
      "Dedicated pilot support",
    ],
    cta: "Apply for Pilot",
    isPopular: true,
  },
  {
    name: "Enterprise Rollout",
    price: "Custom",
    period: "",
    description:
      "Best for organizations preparing for broader access, permissions, integrations, and formal onboarding.",
    features: [
      "Everything in Operations Pilot",
      "SSO and role-based access",
      "Custom data connectors",
      "Reseller and white-label options",
      "SLA and dedicated support",
      "Formal onboarding program",
    ],
    cta: "Plan Rollout",
    isPopular: false,
  },
];
```

- [ ] **Step 6: Replace FAQ_ITEMS**

Replace `FAQ_ITEMS`:

```typescript
export const FAQ_ITEMS: FAQItem[] = [
  {
    question: "Who is DataPulse for?",
    answer:
      "DataPulse is built for commercial, analytics, and operations teams that need one trusted view across sales, branch performance, inventory signals, and operational reporting. It is particularly well suited to pharma and retail operations groups.",
  },
  {
    question: "Do we need clean data before using it?",
    answer:
      "No. DataPulse is designed to help teams start with real-world spreadsheets and operational inputs, then clean and validate them in a structured flow. You do not need to prepare your data in advance.",
  },
  {
    question: "Is this only for dashboards?",
    answer:
      "No. The product supports daily decisions through dashboards, alerts, reporting, and operational visibility. It is meant to be an active tool for teams making commercial and operational decisions.",
  },
  {
    question: "Can it support branch and product-level monitoring?",
    answer:
      "Yes. Branch performance, product movement, and exception visibility are core to the product. You can drill from an executive summary down to branch and product detail.",
  },
  {
    question: "What happens during a pilot?",
    answer:
      "A pilot focuses on a defined use case, a manageable data scope, and clear success criteria so your team can measure value quickly. We work with you to define what a successful pilot looks like before starting.",
  },
  {
    question: "Is the platform secure?",
    answer:
      "DataPulse is built with role-aware access, row-level data isolation, auditability, and enterprise-minded controls so teams can trust how commercial and operational data is handled.",
  },
  {
    question: "How long does it take to see value?",
    answer:
      "Most teams see their first useful dashboard within hours of importing their first data file. A full pilot covering revenue visibility, inventory monitoring, and reporting typically shows value within one to two weeks.",
  },
  {
    question: "Can we connect live data sources?",
    answer:
      "Yes. The Control Center supports managed source connections alongside manual file imports. Connected sources sync automatically on a schedule you control.",
  },
];
```

- [ ] **Step 7: Update FOOTER_COLUMNS**

Replace `FOOTER_COLUMNS` to reflect new nav structure:

```typescript
export const FOOTER_COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "How It Works",  href: "#how-it-works"  },
      { label: "Use Cases",     href: "#use-cases"     },
      { label: "Pilot Access",  href: "#pilot-access"  },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About",   href: "/#how-it-works"                    },
      { label: "Contact", href: "mailto:info@smartdatapulse.tech" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy",   href: "/privacy" },
      { label: "Terms of Service", href: "/terms"   },
    ],
  },
] as const;
```

- [ ] **Step 8: Commit constants changes**

```bash
cd frontend
git add src/lib/marketing-constants.ts
git commit -m "feat(marketing): update all content constants to pharma-first messaging"
```

---

## Task 3: Update hero-section.tsx

**Files:**
- Modify: `frontend/src/components/marketing/hero-section.tsx`

- [ ] **Step 1: Update KPI_ITEMS, eyebrow, headline, and subheadline**

Open `frontend/src/components/marketing/hero-section.tsx`.

Replace the constants at the top of the file:

```typescript
const KPI_ITEMS = [
  { label: "Faster weekly reporting",          value: "Automated" },
  { label: "Earlier stock & expiry visibility",value: "30+ days"  },
  { label: "View across sales & operations",   value: "One system"},
];
```

- [ ] **Step 2: Update eyebrow text**

Find the eyebrow `<div>` (the pill-shaped badge at the top of the hero). Replace its text content:

```tsx
{/* Eyebrow */}
<div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-accent shadow-[0_10px_30px_rgba(0,199,242,0.12)]">
  <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
  Built for pharma sales and operations teams
</div>
```

- [ ] **Step 3: Replace headline**

Find the `<h1>` element. Replace it entirely:

```tsx
<h1 className="max-w-4xl text-4xl font-bold leading-[1.02] tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
  Turn pharma sales and operations data into{" "}
  <span className="gradient-text-animated">daily decisions</span>
</h1>
```

- [ ] **Step 4: Replace subheadline**

Find the `<p>` that wraps `<TypingSubtitle>`. Replace with static text (remove the typing animation — it conflicts with the calm, credible voice):

```tsx
<p className="mt-6 max-w-2xl text-lg text-text-secondary sm:text-xl">
  Upload spreadsheets or connect your data sources, clean them automatically,
  monitor revenue, branch performance, inventory health, and expiry risk, and
  give your team one dashboard they can act on every day.
</p>
```

- [ ] **Step 5: Update CTA buttons**

Find the CTA button group (`<div className="mt-10 flex flex-col...">`). Replace the buttons:

```tsx
<div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-start">
  <Link
    href="#pilot-access"
    className="rounded-full bg-accent px-8 py-3.5 text-sm font-semibold text-page shadow-[0_0_24px_rgba(0,199,242,0.35)] transition-all hover:shadow-[0_0_32px_rgba(0,199,242,0.5)] hover:scale-[1.02]"
  >
    Request Pilot Access
  </Link>
  <Link
    href="/demo"
    className="rounded-full border border-white/15 bg-white/5 px-8 py-3.5 text-sm font-semibold text-text-primary transition-colors hover:bg-white/10"
  >
    See Product Demo
  </Link>
</div>
```

- [ ] **Step 6: Remove TypingSubtitle import if unused**

Check if `TypingSubtitle` is used anywhere else in the file. If not, remove the import:

```typescript
// Remove this line:
// import { TypingSubtitle } from "./typing-subtitle";
```

- [ ] **Step 7: Add supporting note below CTAs**

After the CTA div, add:

```tsx
<p className="mt-4 text-sm text-text-secondary/70">
  Best for commercial leaders, operations teams, and pharmacy groups that need
  clearer decisions without rebuilding their data stack from scratch.
</p>
```

- [ ] **Step 8: Commit hero changes**

```bash
git add src/components/marketing/hero-section.tsx
git commit -m "feat(marketing): update hero section with pharma-first headline and CTAs"
```

---

## Task 4: Rebuild trust-bar.tsx

**Files:**
- Modify: `frontend/src/components/marketing/trust-bar.tsx`

- [ ] **Step 1: Replace trust-bar.tsx entirely**

The current component does a scrolling logo animation for placeholder company names. Replace the whole file:

```typescript
export function TrustBar() {
  const USE_CASES = [
    "Branch performance",
    "Product movement",
    "Stock visibility",
    "Expiry exposure",
    "Supplier workflows",
    "Purchasing operations",
  ];

  return (
    <section className="border-y border-white/10 bg-white/[0.03] py-8 backdrop-blur-sm">
      <p className="mb-5 text-center text-sm font-medium text-text-secondary">
        Built for teams that manage:
      </p>
      <div className="mx-auto flex max-w-4xl flex-wrap justify-center gap-3 px-4">
        {USE_CASES.map((item) => (
          <span
            key={item}
            className="rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-text-secondary/80"
          >
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/marketing/trust-bar.tsx
git commit -m "feat(marketing): replace placeholder trust logos with pharma use-case tags"
```

---

## Task 5: Rebuild stats-banner.tsx as qualitative claims

**Files:**
- Modify: `frontend/src/components/marketing/stats-banner.tsx`

The current component renders animated numeric counters. We're replacing with a qualitative claims grid. The `CLAIMS` constant was added in Task 2.

- [ ] **Step 1: Replace stats-banner.tsx entirely**

```typescript
"use client";

import { SectionWrapper } from "./section-wrapper";
import { CLAIMS } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";
import {
  Clock,
  Eye,
  AlertTriangle,
  Zap,
  type LucideIcon,
} from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  Clock,
  Eye,
  AlertTriangle,
  Zap,
};

export function StatsBanner() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper variant="gradient">
      <div
        ref={ref}
        className={`viz-panel rounded-[2rem] px-6 py-12 backdrop-blur transition-opacity duration-700 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        <div className="absolute inset-x-8 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-blue via-accent to-chart-purple" />
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {CLAIMS.map((claim) => {
            const Icon = ICON_MAP[claim.icon];
            return (
              <div key={claim.headline} className="flex flex-col gap-2">
                {Icon && <Icon className="h-5 w-5 text-accent" />}
                <p className="text-base font-semibold text-text-primary leading-snug">
                  {claim.headline}
                </p>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {claim.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </SectionWrapper>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/marketing/stats-banner.tsx
git commit -m "feat(marketing): replace vanity stats with qualitative operational claims"
```

---

## Task 6: Update cta-section.tsx

**Files:**
- Modify: `frontend/src/components/marketing/cta-section.tsx`

- [ ] **Step 1: Replace the copy and add Phase 4 marker**

Open `frontend/src/components/marketing/cta-section.tsx`. Replace the inner content of the `<div className="relative">` block:

```tsx
<div className="relative">
  <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
    Start with clarity
  </p>
  <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
    See what your team should act on every day.
  </h2>
  <p className="mx-auto mt-4 max-w-xl text-lg leading-8 text-text-secondary">
    If your sales and operations data lives across spreadsheets, manual reports,
    and disconnected workflows, DataPulse can help you turn it into one clearer
    operating view.
  </p>
  <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
    {/* PHASE 4: Replace with <LeadCaptureModal trigger="Request Pilot Access" /> */}
    <a
      href="#pilot-access"
      className="rounded-full bg-accent px-8 py-3.5 text-sm font-semibold text-page shadow-[0_0_24px_rgba(0,199,242,0.35)] transition-all hover:shadow-[0_0_32px_rgba(0,199,242,0.5)] hover:scale-[1.02]"
    >
      Request Pilot Access
    </a>
    <a
      href="/demo"
      className="rounded-full border border-white/15 bg-white/5 px-8 py-3.5 text-sm font-semibold text-text-primary transition-colors hover:bg-white/10"
    >
      See Product Demo
    </a>
  </div>
  <p className="mt-4 text-sm text-text-secondary/70">
    Best for teams that want to prove value in a focused rollout before
    expanding company-wide.
  </p>
</div>
```

- [ ] **Step 2: Remove WaitlistForm import if no longer used**

```typescript
// Remove this line if WaitlistForm is no longer referenced:
// import { WaitlistForm } from "./waitlist-form";
```

- [ ] **Step 3: Commit**

```bash
git add src/components/marketing/cta-section.tsx
git commit -m "feat(marketing): update CTA section with pharma-first copy and Phase 4 marker"
```

---

## Task 7: Update navbar.tsx with dual CTAs

**Files:**
- Modify: `frontend/src/components/marketing/navbar.tsx`
- Modify: `frontend/src/lib/marketing-constants.ts` (NAV_LINKS already updated in Task 2)

- [ ] **Step 1: Find the desktop CTA area in navbar.tsx**

Open `frontend/src/components/marketing/navbar.tsx`. Find the desktop nav area after the `NAV_LINKS.map(...)` block. There is likely a "Get Started" button. Replace the CTA area with dual buttons:

```tsx
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
```

- [ ] **Step 2: Update mobile menu CTAs**

Find the mobile menu section. Replace any "Get Started" link in the mobile menu with:

```tsx
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
```

- [ ] **Step 3: Commit**

```bash
git add src/components/marketing/navbar.tsx
git commit -m "feat(marketing): add dual CTA buttons (See Demo + Request Pilot Access) to navbar"
```

---

## Task 8: Update page.tsx — metadata, remove TechBadges, add Phase 4 marker

**Files:**
- Modify: `frontend/src/app/(marketing)/page.tsx`

- [ ] **Step 1: Update metadata and remove TechBadges**

Open `frontend/src/app/(marketing)/page.tsx`. Replace the entire file:

```typescript
import { HeroSection }    from "@/components/marketing/hero-section";
import { TrustBar }       from "@/components/marketing/trust-bar";
import { FeaturesGrid }   from "@/components/marketing/features-grid";
import { HowItWorks }     from "@/components/marketing/how-it-works";
import { StatsBanner }    from "@/components/marketing/stats-banner";
import { PricingSection } from "@/components/marketing/pricing-section";
import { FAQSection }     from "@/components/marketing/faq-section";
import { CTASection }     from "@/components/marketing/cta-section";
import { JsonLd }         from "@/components/marketing/json-ld";
import type { Metadata }  from "next";

export const metadata: Metadata = {
  title: "DataPulse — Pharma Sales and Operations Intelligence",
  description:
    "DataPulse helps pharma and retail operations teams turn messy sales and inventory data into daily decision-ready intelligence. Upload spreadsheets or connect sources, monitor revenue, track inventory and expiry, and act on what matters.",
  alternates: {
    canonical: "/",
  },
};

export default function LandingPage() {
  return (
    <>
      <JsonLd />
      <HeroSection />
      <TrustBar />
      <FeaturesGrid />
      <HowItWorks />
      <StatsBanner />
      {/* PHASE 4: Add <UseCasesSection /> here before PricingSection */}
      <PricingSection />
      <FAQSection />
      {/* PHASE 4: LeadCaptureModal is wired in CTASection and PricingSection */}
      <CTASection />
    </>
  );
}
```

Note: `TechBadges` import removed. It was technical noise (listing Next.js, PostgreSQL, dbt etc.) — not appropriate for a pharma-first commercial page.

- [ ] **Step 2: Update PricingSection section ID**

Open `frontend/src/components/marketing/pricing-section.tsx`. Find `<SectionWrapper id="pricing">` and change to `<SectionWrapper id="pilot-access">`. Also update the heading:

Find:
```tsx
<p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
  Pricing
</p>
<h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
  Simple, transparent{" "}
  <span className="gradient-text">pricing</span>
</h2>
<p className="mx-auto mt-4 max-w-2xl text-lg leading-8 text-text-secondary">
  Start free, scale when you need to. No hidden fees, no surprises.
</p>
```

Replace with:
```tsx
<p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
  Pilot access
</p>
<h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
  Start with a focused rollout,{" "}
  <span className="gradient-text">not a bloated implementation</span>
</h2>
<p className="mx-auto mt-4 max-w-2xl text-lg leading-8 text-text-secondary">
  DataPulse is best introduced through a focused pilot that proves value quickly
  for one team, one workflow, or one operating region.
</p>
```

- [ ] **Step 3: Commit**

```bash
git add src/app/(marketing)/page.tsx src/components/marketing/pricing-section.tsx
git commit -m "feat(marketing): update page metadata, remove TechBadges, rename pricing to pilot-access"
```

---

## Task 9: Run Acceptance Tests

- [ ] **Step 1: Start the dev server**

```bash
cd frontend
npm run dev
```

Wait for the server to start on `http://localhost:3000`.

- [ ] **Step 2: Run the full marketing E2E spec**

In a second terminal:

```bash
cd frontend
npx playwright test e2e/marketing.spec.ts --reporter=list
```

Expected: all tests PASS.

- [ ] **Step 3: Fix any failing tests**

If a test fails, the error message will name the missing/wrong element. Common fixes:
- If `#pilot-access` section not found → check `pricing-section.tsx` SectionWrapper id was updated
- If "Request Pilot Access" CTA not found → check `hero-section.tsx` and `navbar.tsx` Link text
- If "Explorer Pilot" not found → check `PRICING_TIERS` in constants and the `PricingCard` component renders `tier.name`
- If `branch performance` not found → check `trust-bar.tsx` USE_CASES array

- [ ] **Step 4: TypeScript check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 0 errors. If `STATS` is still imported somewhere (e.g. `stats-banner.tsx` old import), remove it.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(phase1): market clarity complete — pharma-first landing page"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Headline Option A implemented
- ✅ All nav links updated (Product / How It Works / Use Cases / Pilot Access / FAQ)
- ✅ Trust bar placeholder content removed
- ✅ Features: 6 cards with pharma-first copy
- ✅ How It Works: 4-step operational flow
- ✅ Stats: replaced with qualitative claims
- ✅ Pricing → Pilot Access: 3 tiers (Explorer / Operations / Enterprise Rollout)
- ✅ FAQ: 8 pharma-first Q&As
- ✅ CTA section: new copy + Phase 4 marker
- ✅ Navbar: dual CTAs (See Demo + Request Pilot Access)
- ✅ Metadata updated
- ✅ TechBadges removed
- ✅ Phase 4 comment markers placed in page.tsx and cta-section.tsx

**Type consistency:**
- `CLAIMS` (new) referenced in `stats-banner.tsx` Task 5 — consistent
- `PRICING_TIERS` type `PricingTier` unchanged — `PricingCard` component props still match
- `ClaimItem` type added in constants, used in stats-banner — consistent
- `STATS` / `Stat` type removed from constants — remove any remaining imports in stats-banner (Task 5 replaces the whole file so no stale imports)
