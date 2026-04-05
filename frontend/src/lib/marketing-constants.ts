import type { LucideIcon } from "lucide-react";

export const SITE_NAME = "Data Pulse";
export const SITE_DESCRIPTION =
  "Import, clean, analyze, and visualize your sales data with an automated medallion pipeline. AI-powered insights, real-time dashboards, and enterprise-grade quality gates.";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://smartdatapulse.tech";

export const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
] as const;

export const FOOTER_COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "#features" },
      { label: "Pricing", href: "#pricing" },
      { label: "Dashboard", href: "/dashboard" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/#how-it-works" },
      { label: "Contact", href: "mailto:support@smartdatapulse.tech" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Terms of Service", href: "/terms" },
    ],
  },
  {
    title: "Connect",
    links: [
      { label: "GitHub", href: "https://github.com/ahmed-shaaban-94/SAAS" },
    ],
  },
] as const;

export interface FeatureItem {
  icon: string;
  title: string;
  description: string;
}

export const FEATURES: FeatureItem[] = [
  {
    icon: "FileUp",
    title: "Upload & Import",
    description:
      "Import Excel and CSV files with automatic schema detection and type inference.",
  },
  {
    icon: "Sparkles",
    title: "Data Cleaning",
    description:
      "Automated deduplication, normalization, and validation through the silver layer.",
  },
  {
    icon: "ShieldCheck",
    title: "Quality Gates",
    description:
      "7 automated quality checks ensure data integrity at every pipeline stage.",
  },
  {
    icon: "BarChart3",
    title: "Real-time Analytics",
    description:
      "Interactive dashboards with KPIs, trends, rankings, and drill-downs.",
  },
  {
    icon: "Brain",
    title: "AI Insights",
    description:
      "AI-powered anomaly detection and narrative summaries of your sales data.",
  },
  {
    icon: "GitBranch",
    title: "Pipeline Automation",
    description:
      "File watcher auto-triggers the full data pipeline from import to dashboard.",
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
    label: "Import",
    layer: "Bronze",
    description: "Raw data ingestion from Excel and CSV files",
  },
  {
    number: 2,
    icon: "Sparkles",
    label: "Clean",
    layer: "Silver",
    description: "Deduplication, normalization, and type casting",
  },
  {
    number: 3,
    icon: "BarChart3",
    label: "Analyze",
    layer: "Gold",
    description: "Aggregations, KPIs, and business metrics",
  },
  {
    number: 4,
    icon: "Monitor",
    label: "Visualize",
    layer: "Dashboard",
    description: "Interactive charts, tables, and AI insights",
  },
];

export interface Stat {
  value: string;
  numericValue: number;
  suffix: string;
  label: string;
}

export const STATS: Stat[] = [
  { value: "2.2M+", numericValue: 2200000, suffix: "+", label: "Rows Processed" },
  { value: "99.5%", numericValue: 99.5, suffix: "%", label: "Data Quality Score" },
  { value: "10x", numericValue: 10, suffix: "x", label: "Faster than Pandas" },
  { value: "25+", numericValue: 25, suffix: "+", label: "API Endpoints" },
];

export interface PricingTier {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  isPopular: boolean;
}

export const PRICING_TIERS: PricingTier[] = [
  {
    name: "Starter",
    price: "$0",
    period: "/mo",
    description: "Perfect for trying out Data Pulse",
    features: [
      "1 data source",
      "10,000 rows",
      "Basic dashboard",
      "Daily quality checks",
      "Community support",
    ],
    cta: "Get Started Free",
    isPopular: false,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/mo",
    description: "For growing teams and businesses",
    features: [
      "5 data sources",
      "1,000,000 rows",
      "AI-powered insights",
      "Pipeline automation",
      "Quality gates",
      "Priority support",
    ],
    cta: "Start Free Trial",
    isPopular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For large-scale operations",
    features: [
      "Unlimited data sources",
      "Unlimited rows",
      "SSO & RBAC",
      "Custom integrations",
      "Dedicated support",
      "On-premise option",
    ],
    cta: "Contact Sales",
    isPopular: false,
  },
];

export interface FAQItem {
  question: string;
  answer: string;
}

export const FAQ_ITEMS: FAQItem[] = [
  {
    question: "What data formats does Data Pulse support?",
    answer:
      "Data Pulse supports Excel (.xlsx, .xls) and CSV files. Our import engine uses Polars with PyArrow for blazing-fast processing of files up to 500 MB with automatic schema detection.",
  },
  {
    question: "How does the medallion architecture work?",
    answer:
      "Data flows through three layers: Bronze (raw import), Silver (cleaned and validated via dbt), and Gold (aggregated business metrics). Each layer has quality gates to ensure data integrity.",
  },
  {
    question: "What quality checks are included?",
    answer:
      "7 automated checks run at each pipeline stage: row count validation, null rate analysis, schema drift detection, duplicate detection, value range checks, referential integrity, and freshness monitoring.",
  },
  {
    question: "Can I use my own AI/LLM provider?",
    answer:
      "Yes. Data Pulse uses OpenRouter which gives you access to multiple AI models. You can configure your preferred provider and model in the settings.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Absolutely. Data Pulse uses tenant-scoped Row Level Security (RLS) on all database tables, CORS protection, Content Security Policy headers, and all credentials are managed via environment variables.",
  },
  {
    question: "How long does setup take?",
    answer:
      "Under 5 minutes. Run docker compose up and your entire stack is ready: PostgreSQL, the API, dashboard, pipeline automation, and AI insights.",
  },
  {
    question: "What's included in the free tier?",
    answer:
      "The Starter plan includes 1 data source, up to 10,000 rows, the basic analytics dashboard, daily quality checks, and community support. No credit card required.",
  },
  {
    question: "Do you offer custom integrations?",
    answer:
      "Enterprise customers get custom integrations including SSO, webhook notifications, custom data connectors, and dedicated n8n workflow templates for their specific pipeline needs.",
  },
];

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
