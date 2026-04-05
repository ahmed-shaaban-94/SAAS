import {
  FileUp,
  Sparkles,
  ShieldCheck,
  BarChart3,
  Brain,
  GitBranch,
} from "lucide-react";
import type { FeatureItem } from "@/lib/marketing-constants";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  FileUp,
  Sparkles,
  ShieldCheck,
  BarChart3,
  Brain,
  GitBranch,
};

export function FeatureCard({ icon, title, description }: FeatureItem) {
  const Icon = iconMap[icon];

  return (
    <div className="glow-card hover-lift group rounded-xl border border-border bg-card p-6 transition-all">
      <div className="mb-4 inline-flex rounded-lg bg-accent/10 p-3 transition-colors group-hover:bg-accent/20">
        {Icon && (
          <Icon className="h-6 w-6 text-accent transition-transform group-hover:scale-110" />
        )}
      </div>
      <h3 className="mb-2 text-lg font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-text-secondary">{description}</p>
    </div>
  );
}
