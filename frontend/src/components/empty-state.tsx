interface EmptyStateProps {
  title?: string;
  description?: string;
}

function EmptyIllustration() {
  return (
    <svg
      width="80"
      height="80"
      viewBox="0 0 80 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-accent"
      aria-hidden="true"
    >
      {/* Chart bars with staggered grow animation */}
      <rect x="12" y="52" width="10" height="16" rx="3" fill="currentColor" opacity="0.15">
        <animate attributeName="height" values="0;16;16" dur="0.8s" fill="freeze" />
        <animate attributeName="y" values="68;52;52" dur="0.8s" fill="freeze" />
      </rect>
      <rect x="26" y="40" width="10" height="28" rx="3" fill="currentColor" opacity="0.25">
        <animate attributeName="height" values="0;28;28" dur="0.8s" begin="0.15s" fill="freeze" />
        <animate attributeName="y" values="68;40;40" dur="0.8s" begin="0.15s" fill="freeze" />
      </rect>
      <rect x="40" y="32" width="10" height="36" rx="3" fill="currentColor" opacity="0.35">
        <animate attributeName="height" values="0;36;36" dur="0.8s" begin="0.3s" fill="freeze" />
        <animate attributeName="y" values="68;32;32" dur="0.8s" begin="0.3s" fill="freeze" />
      </rect>
      <rect x="54" y="44" width="10" height="24" rx="3" fill="currentColor" opacity="0.2">
        <animate attributeName="height" values="0;24;24" dur="0.8s" begin="0.45s" fill="freeze" />
        <animate attributeName="y" values="68;44;44" dur="0.8s" begin="0.45s" fill="freeze" />
      </rect>

      {/* Dashed line across */}
      <line x1="8" y1="68" x2="68" y2="68" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.3" />

      {/* Magnifying glass */}
      <circle cx="58" cy="22" r="10" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.4">
        <animate attributeName="r" values="8;10;8" dur="3s" repeatCount="indefinite" />
      </circle>
      <line x1="65" y1="29" x2="72" y2="36" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
    </svg>
  );
}

export function EmptyState({
  title = "No data available",
  description = "Try adjusting your filters or check back later.",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border border-dashed bg-card/50 backdrop-blur-sm p-16 animate-fade-in">
      <EmptyIllustration />
      <h3 className="mt-5 text-lg font-semibold text-text-primary">{title}</h3>
      <p className="mt-1.5 max-w-sm text-center text-sm text-text-secondary">{description}</p>
    </div>
  );
}
