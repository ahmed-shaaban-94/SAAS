"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createVoucher } from "@/hooks/use-vouchers";
import type { VoucherCreateInput, VoucherType } from "@/types/vouchers";

const CODE_PATTERN = /^[A-Z0-9_-]+$/;

interface FieldErrors {
  code?: string;
  value?: string;
  submit?: string;
}

export default function NewVoucherPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [discountType, setDiscountType] = useState<VoucherType>("amount");
  const [value, setValue] = useState<string>("");
  const [maxUses, setMaxUses] = useState<string>("1");
  const [startsAt, setStartsAt] = useState<string>("");
  const [endsAt, setEndsAt] = useState<string>("");
  const [minPurchase, setMinPurchase] = useState<string>("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const e: FieldErrors = {};
    if (code.length < 3 || code.length > 64) {
      e.code = "Code must be 3-64 characters.";
    } else if (!CODE_PATTERN.test(code)) {
      e.code = "Code may only contain A-Z, 0-9, _ and -.";
    }
    const v = Number(value);
    if (!value || Number.isNaN(v) || v <= 0) {
      e.value = "Value must be greater than zero.";
    } else if (discountType === "percent" && v > 100) {
      e.value = "Percent value must be ≤ 100.";
    }
    return e;
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    const payload: VoucherCreateInput = {
      code,
      discount_type: discountType,
      value: Number(value),
      max_uses: Number(maxUses) || 1,
      starts_at: startsAt ? new Date(startsAt).toISOString() : null,
      ends_at: endsAt ? new Date(endsAt).toISOString() : null,
      min_purchase: minPurchase ? Number(minPurchase) : null,
    };

    setSubmitting(true);
    try {
      await createVoucher(payload);
      router.push("/settings/vouchers");
    } catch (err) {
      setErrors({
        submit:
          err instanceof Error ? err.message : "Failed to create voucher. Please try again.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-semibold mb-1">New voucher</h1>
      <p className="text-sm text-zinc-400 mb-6">
        Create a discount code that cashiers can redeem at checkout.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <label htmlFor="code" className="block text-sm font-medium mb-1">
            Code
          </label>
          <input
            id="code"
            name="code"
            type="text"
            required
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md font-mono"
            placeholder="SUMMER25"
          />
          {errors.code && (
            <p className="text-xs text-red-400 mt-1" role="alert">
              {errors.code}
            </p>
          )}
        </div>

        <fieldset>
          <legend className="block text-sm font-medium mb-1">Discount type</legend>
          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="discount_type"
                value="amount"
                checked={discountType === "amount"}
                onChange={() => setDiscountType("amount")}
              />
              <span>Amount (EGP)</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="discount_type"
                value="percent"
                checked={discountType === "percent"}
                onChange={() => setDiscountType("percent")}
              />
              <span>Percent</span>
            </label>
          </div>
        </fieldset>

        <div>
          <label htmlFor="value" className="block text-sm font-medium mb-1">
            Value {discountType === "percent" ? "(%)" : "(EGP)"}
          </label>
          <input
            id="value"
            name="value"
            type="number"
            required
            min={0.01}
            max={discountType === "percent" ? 100 : undefined}
            step={0.01}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
          />
          {errors.value && (
            <p className="text-xs text-red-400 mt-1" role="alert">
              {errors.value}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="max_uses" className="block text-sm font-medium mb-1">
            Max uses
          </label>
          <input
            id="max_uses"
            name="max_uses"
            type="number"
            min={1}
            step={1}
            value={maxUses}
            onChange={(e) => setMaxUses(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="starts_at" className="block text-sm font-medium mb-1">
              Starts at (optional)
            </label>
            <input
              id="starts_at"
              name="starts_at"
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            />
          </div>
          <div>
            <label htmlFor="ends_at" className="block text-sm font-medium mb-1">
              Ends at (optional)
            </label>
            <input
              id="ends_at"
              name="ends_at"
              type="datetime-local"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            />
          </div>
        </div>

        <div>
          <label htmlFor="min_purchase" className="block text-sm font-medium mb-1">
            Minimum purchase (EGP, optional)
          </label>
          <input
            id="min_purchase"
            name="min_purchase"
            type="number"
            min={0}
            step={0.01}
            value={minPurchase}
            onChange={(e) => setMinPurchase(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
          />
        </div>

        {errors.submit && (
          <p className="text-sm text-red-400" role="alert">
            {errors.submit}
          </p>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-accent text-white hover:opacity-90 transition disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create voucher"}
          </button>
          <button
            type="button"
            onClick={() => router.push("/settings/vouchers")}
            className="px-4 py-2 rounded-md border border-zinc-700 hover:bg-zinc-800 transition"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
