"use client";

import { useState } from "react";
import { ShieldCheck, Loader2 } from "lucide-react";
import { postAPI } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { PharmacistVerifyResponse } from "@/types/pos";

interface PharmacistVerificationProps {
  open: boolean;
  drugCode: string;
  onVerified: (pharmacistId: string) => void;
  onCancel: () => void;
}

const PIN_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "CLR", "0", "⌫"] as const;

export function PharmacistVerification({
  open,
  drugCode,
  onVerified,
  onCancel,
}: PharmacistVerificationProps) {
  const [pin, setPin] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  function handleKey(key: string) {
    setError(null);
    if (key === "CLR") { setPin(""); return; }
    if (key === "⌫") { setPin((p) => p.slice(0, -1)); return; }
    if (pin.length < 6) setPin((p) => p + key);
  }

  async function handleVerify() {
    if (!pin) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await postAPI<PharmacistVerifyResponse>("/api/v1/pos/verify-pharmacist", {
        drug_code: drugCode,
        pin,
      });
      if (res.verified) {
        setPin("");
        onVerified(res.pharmacist_id);
      } else {
        setError("PIN not recognised");
      }
    } catch {
      setError("Verification failed — try again");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-6 shadow-2xl">
        <div className="mb-4 flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/20">
            <ShieldCheck className="h-6 w-6 text-amber-400" />
          </div>
          <h2 className="text-base font-semibold text-text-primary">Pharmacist Verification</h2>
          <p className="text-center text-xs text-text-secondary">
            Controlled substance requires pharmacist PIN
          </p>
        </div>

        {/* PIN display */}
        <div className="mb-4 flex justify-center gap-2">
          {Array.from({ length: 6 }, (_, i) => (
            <div
              key={i}
              className={cn(
                "h-3 w-3 rounded-full border-2",
                i < pin.length ? "border-accent bg-accent" : "border-border",
              )}
            />
          ))}
        </div>

        {/* PIN pad */}
        <div className="mb-4 grid grid-cols-3 gap-2">
          {PIN_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => handleKey(key)}
              disabled={isLoading}
              className={cn(
                "flex min-h-[3rem] items-center justify-center rounded-xl text-sm font-semibold",
                "bg-surface-raised hover:bg-surface-raised/80 active:scale-95 transition-all duration-100",
                "disabled:pointer-events-none disabled:opacity-40",
              )}
            >
              {key}
            </button>
          ))}
        </div>

        {error && <p className="mb-3 text-center text-xs text-destructive">{error}</p>}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 rounded-xl border border-border py-2.5 text-sm font-medium text-text-secondary hover:bg-surface-raised"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleVerify}
            disabled={isLoading || pin.length < 4}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold",
              "bg-accent text-accent-foreground shadow-[0_8px_24px_rgba(0,199,242,0.2)]",
              "disabled:pointer-events-none disabled:opacity-40 hover:bg-accent/90",
            )}
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Verify"}
          </button>
        </div>
      </div>
    </div>
  );
}
