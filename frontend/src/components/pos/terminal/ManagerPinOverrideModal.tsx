"use client";

/**
 * ManagerPinOverrideModal — PIN gate for destructive cart actions (issue #632, D5).
 *
 * Accepts a 4-6 digit PIN typed by the manager; auto-submits on Enter.
 * Calls POST /api/v1/rbac/verify-pin — backend sub-issue to be filed if
 * the endpoint doesn't exist yet (no hard-coded PINs).
 *
 * Usage:
 *   <ManagerPinOverrideModal
 *     open={overrideOpen}
 *     actionLabel="حذف صنف"
 *     onApproved={() => { doDestructiveAction(); setOverrideOpen(false); }}
 *     onCancel={() => setOverrideOpen(false)}
 *   />
 */

import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ChangeEvent,
} from "react";
import { Lock, Loader2 } from "lucide-react";
import { postAPI } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface ManagerPinOverrideModalProps {
  open: boolean;
  /** Short description shown below the heading, e.g. "حذف صنف من السلة" */
  actionLabel: string;
  onApproved: () => void;
  onCancel: () => void;
}

interface VerifyPinResponse {
  approved: boolean;
}

export function ManagerPinOverrideModal({
  open,
  actionLabel,
  onApproved,
  onCancel,
}: ManagerPinOverrideModalProps) {
  const [pin, setPin] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setPin("");
      setError(null);
      // Defer so the DOM is visible before focusing
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  if (!open) return null;

  async function handleVerify() {
    if (pin.length < 4) {
      setError("الرقم السري 4–6 أرقام");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      // POST /api/v1/rbac/verify-pin — backend sub-issue tracked separately.
      const res = await postAPI<VerifyPinResponse>("/api/v1/rbac/verify-pin", { pin });
      if (res.approved) {
        setPin("");
        onApproved();
      } else {
        setError("رمز PIN غير صحيح");
        setPin("");
        setTimeout(() => inputRef.current?.focus(), 50);
      }
    } catch {
      setError("فشل التحقق — حاول مجدداً");
      setPin("");
      setTimeout(() => inputRef.current?.focus(), 50);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: ReactKeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      void handleVerify();
    }
    if (e.key === "Escape") {
      onCancel();
    }
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const val = e.target.value.replace(/\D/g, "").slice(0, 6);
    setError(null);
    setPin(val);
    if (val.length === 6) {
      // Auto-submit on reaching max length
      setTimeout(() => void handleVerify(), 10);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-md"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        className={cn(
          "w-full max-w-xs rounded-3xl bg-[var(--pos-card)] p-6 shadow-2xl",
          "border-2 border-amber-400/60",
        )}
        data-testid="manager-pin-modal"
      >
        {/* Icon + heading */}
        <div className="mb-5 flex flex-col items-center gap-2">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-amber-400/10">
            <Lock className="h-7 w-7 text-amber-400" />
          </div>
          <h2 className="pos-display text-[17px] text-text-primary">تفويض المدير</h2>
          <p className="text-center font-mono text-[11px] text-text-secondary">{actionLabel}</p>
        </div>

        {/* PIN dot display */}
        <div className="mb-4 flex justify-center gap-3">
          {Array.from({ length: 6 }, (_, i) => (
            <div
              key={i}
              className={cn(
                "h-3 w-3 rounded-full border-2 transition-all",
                i < pin.length
                  ? "border-amber-400 bg-amber-400"
                  : "border-[var(--pos-line)] bg-transparent",
              )}
            />
          ))}
        </div>

        {/* Hidden password input — keyboard entry */}
        <input
          ref={inputRef}
          type="password"
          inputMode="numeric"
          pattern="[0-9]*"
          value={pin}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          maxLength={6}
          disabled={isLoading}
          className="sr-only"
          aria-label="Manager PIN"
          autoComplete="one-time-code"
        />

        {error && (
          <p className="mb-3 text-center font-mono text-[11px] text-red-400">{error}</p>
        )}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className={cn(
              "flex-1 rounded-xl border border-[var(--pos-line)] py-2.5",
              "font-mono text-[12px] text-text-secondary",
              "hover:border-text-secondary/40 transition",
            )}
          >
            إلغاء
          </button>
          <button
            type="button"
            onClick={() => void handleVerify()}
            disabled={isLoading || pin.length < 4}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5",
              "bg-amber-400 font-mono text-[12px] font-bold text-black",
              "transition hover:bg-amber-300 active:scale-[0.98]",
              "disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "تأكيد"}
          </button>
        </div>
      </div>
    </div>
  );
}
