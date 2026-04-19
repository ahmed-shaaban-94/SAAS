"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { setPromotionStatus, usePromotion } from "@/hooks/use-promotions";
import type { PromotionStatus } from "@/types/promotions";

const STATUS_PILL: Record<PromotionStatus, string> = {
  active: "bg-green-500/20 text-green-400 border-green-500/30",
  paused: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  expired: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatValue(type: "amount" | "percent", value: number): string {
  return type === "percent" ? `${value}%` : `EGP ${value.toFixed(2)}`;
}

export default function PromotionDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params?.id);
  const { data, error, isLoading, mutate } = usePromotion(
    Number.isFinite(id) && id > 0 ? id : null,
  );
  const [busy, setBusy] = useState(false);
  const [flashError, setFlashError] = useState<string | null>(null);

  async function toggleStatus(next: "active" | "paused") {
    if (!data) return;
    setBusy(true);
    setFlashError(null);
    try {
      await setPromotionStatus(data.id, next);
      await mutate();
    } catch (err) {
      setFlashError(err instanceof Error ? err.message : "Failed to update status.");
    } finally {
      setBusy(false);
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 text-sm text-zinc-400" role="status">
        Loading promotion…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="text-sm text-red-400" role="alert">
          Promotion not found.
        </div>
        <Link
          href="/settings/promotions"
          className="inline-block mt-4 text-accent hover:underline"
        >
          ← Back to promotions
        </Link>
      </div>
    );
  }

  const isExpired = data.status === "expired";

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-4">
        <Link
          href="/settings/promotions"
          className="text-sm text-zinc-400 hover:text-zinc-200"
        >
          ← Back to promotions
        </Link>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">{data.name}</h1>
          {data.description && (
            <p className="text-sm text-zinc-400 mt-1">{data.description}</p>
          )}
        </div>
        <span
          className={`inline-block px-2 py-0.5 rounded-full text-xs border ${STATUS_PILL[data.status]}`}
        >
          {data.status}
        </span>
      </div>

      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 border border-zinc-800 rounded-md p-5 mb-6">
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Discount</dt>
          <dd className="text-base">{formatValue(data.discount_type, data.value)}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Scope</dt>
          <dd className="text-base capitalize">{data.scope}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Starts</dt>
          <dd className="text-base">{formatDate(data.starts_at)}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Ends</dt>
          <dd className="text-base">{formatDate(data.ends_at)}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Min purchase</dt>
          <dd className="text-base">
            {data.min_purchase == null ? "—" : `EGP ${data.min_purchase.toFixed(2)}`}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Max discount cap</dt>
          <dd className="text-base">
            {data.max_discount == null ? "—" : `EGP ${data.max_discount.toFixed(2)}`}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Usage count</dt>
          <dd className="text-base">{data.usage_count}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500 uppercase">Total discount given</dt>
          <dd className="text-base">EGP {data.total_discount_given.toFixed(2)}</dd>
        </div>
      </dl>

      {data.scope === "items" && (
        <div className="mb-6">
          <h2 className="text-sm font-medium mb-2">Drug codes in scope</h2>
          <div className="flex flex-wrap gap-2">
            {data.scope_items.length === 0 ? (
              <span className="text-sm text-zinc-500">None</span>
            ) : (
              data.scope_items.map((code) => (
                <span
                  key={code}
                  className="font-mono text-xs px-2 py-0.5 rounded bg-zinc-900 border border-zinc-700"
                >
                  {code}
                </span>
              ))
            )}
          </div>
        </div>
      )}

      {data.scope === "category" && (
        <div className="mb-6">
          <h2 className="text-sm font-medium mb-2">Categories in scope</h2>
          <div className="flex flex-wrap gap-2">
            {data.scope_categories.length === 0 ? (
              <span className="text-sm text-zinc-500">None</span>
            ) : (
              data.scope_categories.map((c) => (
                <span
                  key={c}
                  className="text-xs px-2 py-0.5 rounded bg-zinc-900 border border-zinc-700"
                >
                  {c}
                </span>
              ))
            )}
          </div>
        </div>
      )}

      {flashError && (
        <p className="text-sm text-red-400 mb-3" role="alert">
          {flashError}
        </p>
      )}

      <div className="flex gap-3">
        {data.status === "paused" && !isExpired && (
          <button
            type="button"
            onClick={() => toggleStatus("active")}
            disabled={busy}
            className="px-4 py-2 rounded-md bg-green-600 text-white hover:opacity-90 transition disabled:opacity-50"
          >
            {busy ? "Activating…" : "Activate"}
          </button>
        )}
        {data.status === "active" && (
          <button
            type="button"
            onClick={() => toggleStatus("paused")}
            disabled={busy}
            className="px-4 py-2 rounded-md bg-amber-600 text-white hover:opacity-90 transition disabled:opacity-50"
          >
            {busy ? "Pausing…" : "Pause"}
          </button>
        )}
        <button
          type="button"
          onClick={() => router.push("/settings/promotions")}
          className="px-4 py-2 rounded-md border border-zinc-700 hover:bg-zinc-800 transition"
        >
          Done
        </button>
      </div>
    </div>
  );
}
