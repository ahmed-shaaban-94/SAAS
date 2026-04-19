"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createPromotion } from "@/hooks/use-promotions";
import type {
  PromotionCreateInput,
  PromotionDiscountType,
  PromotionScope,
} from "@/types/promotions";

interface FieldErrors {
  name?: string;
  value?: string;
  dates?: string;
  scope?: string;
  submit?: string;
}

function parseList(raw: string): string[] {
  return raw
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export default function NewPromotionPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [discountType, setDiscountType] = useState<PromotionDiscountType>("amount");
  const [value, setValue] = useState("");
  const [scope, setScope] = useState<PromotionScope>("all");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [minPurchase, setMinPurchase] = useState("");
  const [maxDiscount, setMaxDiscount] = useState("");
  const [itemsRaw, setItemsRaw] = useState("");
  const [categoriesRaw, setCategoriesRaw] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const e: FieldErrors = {};
    if (!name.trim() || name.length > 128) e.name = "Name is required (max 128 chars).";
    const v = Number(value);
    if (!value || Number.isNaN(v) || v <= 0) {
      e.value = "Value must be greater than zero.";
    } else if (discountType === "percent" && v > 100) {
      e.value = "Percent value must be ≤ 100.";
    }
    if (!startsAt || !endsAt) {
      e.dates = "Start and end dates are required.";
    } else if (new Date(endsAt) <= new Date(startsAt)) {
      e.dates = "End date must be after start date.";
    }
    if (scope === "items" && parseList(itemsRaw).length === 0) {
      e.scope = "Add at least one drug code for item-scoped promotions.";
    }
    if (scope === "category" && parseList(categoriesRaw).length === 0) {
      e.scope = "Add at least one category cluster for category-scoped promotions.";
    }
    return e;
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    const payload: PromotionCreateInput = {
      name: name.trim(),
      description: description.trim() || null,
      discount_type: discountType,
      value: Number(value),
      scope,
      starts_at: new Date(startsAt).toISOString(),
      ends_at: new Date(endsAt).toISOString(),
      min_purchase: minPurchase ? Number(minPurchase) : null,
      max_discount: maxDiscount ? Number(maxDiscount) : null,
      scope_items: scope === "items" ? parseList(itemsRaw) : [],
      scope_categories: scope === "category" ? parseList(categoriesRaw) : [],
    };

    setSubmitting(true);
    try {
      await createPromotion(payload);
      router.push("/settings/promotions");
    } catch (err) {
      setErrors({
        submit:
          err instanceof Error ? err.message : "Failed to create promotion. Please try again.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold mb-1">New promotion</h1>
      <p className="text-sm text-zinc-400 mb-6">
        Create a discount campaign. It starts in <b>paused</b> state — activate it from the
        list once you&apos;re ready.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <label htmlFor="name" className="block text-sm font-medium mb-1">
            Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            required
            maxLength={128}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            placeholder="Ramadan 2026"
          />
          {errors.name && (
            <p className="text-xs text-red-400 mt-1" role="alert">
              {errors.name}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium mb-1">
            Description (optional)
          </label>
          <textarea
            id="description"
            name="description"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            placeholder="Customer-facing description"
          />
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

        <fieldset>
          <legend className="block text-sm font-medium mb-1">Scope</legend>
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="scope"
                value="all"
                checked={scope === "all"}
                onChange={() => setScope("all")}
              />
              <span>Entire cart</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="scope"
                value="items"
                checked={scope === "items"}
                onChange={() => setScope("items")}
              />
              <span>Specific drug codes</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="scope"
                value="category"
                checked={scope === "category"}
                onChange={() => setScope("category")}
              />
              <span>Specific categories (drug clusters)</span>
            </label>
          </div>
        </fieldset>

        {scope === "items" && (
          <div>
            <label htmlFor="scope_items" className="block text-sm font-medium mb-1">
              Drug codes (one per line or comma-separated)
            </label>
            <textarea
              id="scope_items"
              rows={4}
              value={itemsRaw}
              onChange={(e) => setItemsRaw(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md font-mono text-sm"
              placeholder="DRUG001&#10;DRUG002"
            />
          </div>
        )}

        {scope === "category" && (
          <div>
            <label htmlFor="scope_categories" className="block text-sm font-medium mb-1">
              Category clusters (one per line or comma-separated)
            </label>
            <textarea
              id="scope_categories"
              rows={4}
              value={categoriesRaw}
              onChange={(e) => setCategoriesRaw(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md font-mono text-sm"
              placeholder="antibiotics&#10;painkillers"
            />
          </div>
        )}

        {errors.scope && (
          <p className="text-xs text-red-400 -mt-2" role="alert">
            {errors.scope}
          </p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="starts_at" className="block text-sm font-medium mb-1">
              Starts at
            </label>
            <input
              id="starts_at"
              name="starts_at"
              type="datetime-local"
              required
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            />
          </div>
          <div>
            <label htmlFor="ends_at" className="block text-sm font-medium mb-1">
              Ends at
            </label>
            <input
              id="ends_at"
              name="ends_at"
              type="datetime-local"
              required
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            />
          </div>
        </div>
        {errors.dates && (
          <p className="text-xs text-red-400 -mt-3" role="alert">
            {errors.dates}
          </p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="min_purchase" className="block text-sm font-medium mb-1">
              Min purchase (EGP, optional)
            </label>
            <input
              id="min_purchase"
              type="number"
              min={0}
              step={0.01}
              value={minPurchase}
              onChange={(e) => setMinPurchase(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            />
          </div>
          <div>
            <label htmlFor="max_discount" className="block text-sm font-medium mb-1">
              Max discount cap (EGP, optional)
            </label>
            <input
              id="max_discount"
              type="number"
              min={0}
              step={0.01}
              value={maxDiscount}
              onChange={(e) => setMaxDiscount(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md"
            />
          </div>
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
            {submitting ? "Creating…" : "Create promotion"}
          </button>
          <button
            type="button"
            onClick={() => router.push("/settings/promotions")}
            className="px-4 py-2 rounded-md border border-zinc-700 hover:bg-zinc-800 transition"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
