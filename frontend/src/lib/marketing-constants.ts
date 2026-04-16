import type { LucideIcon } from "lucide-react";

export const SITE_NAME = "DataPulse";
export const SITE_DESCRIPTION =
  "DataPulse helps pharma and retail operations teams turn messy sales and inventory data into daily decision-ready intelligence.";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://smartdatapulse.tech";

export const NAV_LINKS = [
  { label: "Product",      href: "#features"    },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Use Cases",    href: "#use-cases"   },
  { label: "Pilot Access", href: "#pilot-access" },
  { label: "FAQ",          href: "#faq"         },
] as const;

export interface FeatureItem {
  icon: string;
  title: string;
  description: string;
}

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

export interface PipelineStep {
  number: number;
  icon: string;
  label: string;
  layer: string;
  description: string;
}

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

export interface PricingTier {
  name: string;
  price: string;
  originalPrice?: string;
  period: string;
  description: string;
  badge?: string;
  features: string[];
  cta: string;
  isPopular: boolean;
}

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

export interface FAQItem {
  question: string;
  answer: string;
}

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

export const TECH_BADGES = [
  "Next.js",
  "PostgreSQL",
  "dbt",
  "Polars",
  "FastAPI",
  "Docker",
  "n8n",
  "Recharts",
] as const;
