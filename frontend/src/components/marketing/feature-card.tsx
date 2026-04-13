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
    <div className="viz-panel viz-card-hover glow-card hover-lift group rounded-[1.6rem] p-6 transition-all">
      <div className="mb-5 inline-flex rounded-2xl bg-accent/10 p-3 transition-colors group-hover:bg-accent/18">
        {Icon && (
          <Icon className="h-6 w-6 text-accent transition-transform group-hover:scale-110" />
        )}
      </div>
      <h3 className="mb-3 text-xl font-semibold tracking-tight text-text-primary">{title}</h3>
      <p className="text-sm leading-7 text-text-secondary">{description}</p>
    </div>
  );
}
