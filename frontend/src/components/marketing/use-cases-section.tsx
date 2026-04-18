import { SectionWrapper } from "./section-wrapper";
import { BarChart3, Package, GitBranch, FileBarChart } from "lucide-react";

const USE_CASES = [
  {
    icon: BarChart3,
    title: "Sales & Revenue Reporting",
    description:
      "Turn weekly spreadsheet exports into a live executive overview. Track revenue, product movement, and trend shifts across branches without manual compilation.",
    tag: "Commercial Teams",
  },
  {
    icon: Package,
    title: "Inventory & Expiry Monitoring",
    description:
      "Surface stockout risk and expiry exposure before they affect service levels. Know which products need attention now, not after the problem surfaces.",
    tag: "Operations Teams",
  },
  {
    icon: GitBranch,
    title: "Branch Performance Tracking",
    description:
      "Compare performance across locations. Identify which branches are lagging, which are trending, and where to focus field attention next.",
    tag: "Regional Management",
  },
  {
    icon: FileBarChart,
    title: "Operational Reporting",
    description:
      "Replace manual reporting cycles with scheduled outputs that go to the right people automatically. From daily briefings to monthly reviews.",
    tag: "Reporting Teams",
  },
] as const;

export function UseCasesSection() {
  return (
    <SectionWrapper id="use-cases">
      <div className="mb-12 text-center">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
          Use cases
        </p>
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
          Built for teams that need clarity, not more reports
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-lg leading-8 text-text-secondary">
          DataPulse is used across commercial, operations, and regional management workflows
          in pharma and retail distribution.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        {USE_CASES.map(({ icon: Icon, title, description, tag }) => (
          <div
            key={title}
            className="viz-panel viz-card-hover rounded-[1.5rem] p-6 hover-lift"
          >
            <div className="mb-4 flex items-center gap-3">
              <div className="viz-panel-soft flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
                <Icon className="h-5 w-5 text-accent" />
              </div>
              <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
                {tag}
              </span>
            </div>
            <h3 className="text-base font-semibold text-text-primary">{title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-text-secondary">{description}</p>
          </div>
        ))}
      </div>
    </SectionWrapper>
  );
}
