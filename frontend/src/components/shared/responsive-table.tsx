import { cn } from "@/lib/utils";

interface ResponsiveTableProps {
  children: React.ReactNode;
  className?: string;
}

export function ResponsiveTable({ children, className }: ResponsiveTableProps) {
  return (
    <div className={cn("relative", className)}>
      <div className="overflow-x-auto rounded-lg">
        {children}
      </div>
      {/* Right fade indicator for scroll hint */}
      <div className="pointer-events-none absolute right-0 top-0 h-full w-8 bg-gradient-to-l from-card to-transparent md:hidden" />
    </div>
  );
}
