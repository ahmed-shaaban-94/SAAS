"use client";

import { BarChart3, TrendingUp, Package, Users } from "lucide-react";

interface FirstReportStepProps {
  onComplete: () => void;
}

const templates = [
  {
    name: "Sales Overview",
    description: "Revenue trends, top products, and daily performance",
    icon: TrendingUp,
  },
  {
    name: "Product Performance",
    description: "Product rankings, category breakdowns, and margins",
    icon: Package,
  },
  {
    name: "Customer Analysis",
    description: "Customer segments, retention, and purchase patterns",
    icon: Users,
  },
];

export function FirstReportStep({ onComplete }: FirstReportStepProps) {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-accent/10">
        <BarChart3 className="h-12 w-12 text-accent" />
      </div>

      <h2 className="mb-2 text-xl font-semibold text-text-primary">
        Create Your First Report
      </h2>
      <p className="mb-6 max-w-sm text-sm text-text-secondary">
        Choose a report template to see your data come alive.
      </p>

      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
        {templates.map((template) => {
          const Icon = template.icon;
          return (
            <button
              key={template.name}
              onClick={onComplete}
              className="flex flex-col items-center gap-2 rounded-xl border border-border bg-transparent p-4 text-center transition-colors hover:border-accent/50 hover:bg-accent/5"
            >
              <Icon className="h-8 w-8 text-accent" />
              <span className="text-sm font-medium text-text-primary">
                {template.name}
              </span>
              <span className="text-xs text-text-secondary">
                {template.description}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
