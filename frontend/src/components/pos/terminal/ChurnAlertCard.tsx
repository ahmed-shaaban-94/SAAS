"use client";

import { BrainCircuit } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PosCustomerChurnInfo } from "@/hooks/use-pos-customer-lookup";

/**
 * Churn alert — the red "AI triggers, not AI chatter" card that appears
 * ONLY when an AI-flagged churn risk is attached to the currently
 * resolved customer (v9 handoff §1.3, §Editorial Principles #4).
 *
 * Hidden by default. Don't render this component at all when
 * `churn.risk === false` — the design intent is that silence is the
 * default state.
 */
interface ChurnAlertCardProps {
  churn: PosCustomerChurnInfo;
  className?: string;
}

export function ChurnAlertCard({ churn, className }: ChurnAlertCardProps) {
  if (!churn.risk) return null;

  const firstLate = churn.late_refills[0];
  return (
    <aside
      role="alert"
      aria-live="polite"
      data-testid="churn-alert-card"
      className={cn(
        "flex items-start gap-3 rounded-xl border p-3",
        "border-[var(--pos-red)]/30 bg-[var(--pos-red)]/10",
        className,
      )}
    >
      <BrainCircuit
        className="mt-0.5 h-5 w-5 shrink-0 text-[var(--pos-red)]"
        aria-hidden="true"
      />
      <div className="flex min-w-0 flex-col gap-1">
        <p className="pos-eyebrow text-[var(--pos-red)]">
          Churn Risk · AI detected
        </p>
        {firstLate ? (
          <p
            className="font-arabic text-xs leading-relaxed text-[var(--pos-ink)]"
            dir="rtl"
            data-testid="churn-alert-detail"
          >
            العميل متأخر عن موعد إعادة الصرف لـ{" "}
            <span className="font-bold">{firstLate.drug_name}</span>{" "}
            ({firstLate.days_late.toLocaleString("ar-EG")} أيام تأخير). اسأل
            المريض عن صحته.
          </p>
        ) : (
          <p
            className="font-arabic text-xs text-[var(--pos-ink-2)]"
            dir="rtl"
          >
            هذا العميل معرض للتسرب. راجع تاريخ الصرف السابق وبادر بالمتابعة.
          </p>
        )}
      </div>
    </aside>
  );
}
