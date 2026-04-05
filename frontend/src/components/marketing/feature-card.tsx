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

export function FeatureCard({ icon, title, description, isBento }: FeatureItem & { isBento?: boolean }) {
  const Icon = iconMap[icon];

  return (
    <div className={`glow-card hover-lift group rounded-xl border border-border bg-card p-6 transition-all h-full ${
      isBento ? "flex items-start gap-6" : ""
    }`}>
      <div className={`shrink-0 inline-flex rounded-lg bg-accent/10 p-3 transition-colors group-hover:bg-accent/20 ${
        isBento ? "" : "mb-4"
      }`}>
        {Icon && (
          <Icon className={`text-accent transition-transform group-hover:scale-110 ${
            isBento ? "h-8 w-8" : "h-6 w-6"
          }`} />
        )}
      </div>
      <div>
        <h3 className={`font-semibold ${isBento ? "text-xl mb-3" : "text-lg mb-2"}`}>{title}</h3>
        <p className={`leading-relaxed text-text-secondary ${isBento ? "text-base" : "text-sm"}`}>{description}</p>
      </div>
    </div>
  );
}
