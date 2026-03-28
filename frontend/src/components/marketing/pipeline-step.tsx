import { FileUp, Sparkles, BarChart3, Monitor } from "lucide-react";
import type { PipelineStep } from "@/lib/marketing-constants";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  FileUp,
  Sparkles,
  BarChart3,
  Monitor,
};

export function PipelineStepCard({
  number,
  icon,
  label,
  layer,
  description,
  isLast,
}: PipelineStep & { isLast: boolean }) {
  const Icon = iconMap[icon];

  return (
    <div className={`relative flex flex-1 flex-col items-center text-center ${!isLast ? "pipeline-connector" : ""}`}>
      {/* Number + Icon circle */}
      <div className="relative mb-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-accent/30 bg-accent/10">
          {Icon && <Icon className="h-7 w-7 text-accent" />}
        </div>
        <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-xs font-bold text-page">
          {number}
        </span>
      </div>

      {/* Label */}
      <h3 className="mb-1 text-lg font-semibold">{label}</h3>
      <span className="mb-2 inline-block rounded-full bg-accent/10 px-3 py-0.5 text-xs font-medium text-accent">
        {layer}
      </span>
      <p className="text-sm text-text-secondary">{description}</p>
    </div>
  );
}
