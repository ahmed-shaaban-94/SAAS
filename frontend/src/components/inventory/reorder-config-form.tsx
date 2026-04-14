"use client";

import { useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { useReorderConfig } from "@/hooks/use-reorder-config";
import { cn } from "@/lib/utils";
import type { ReorderConfig, StockLevel } from "@/types/inventory";

interface ReorderConfigFormProps {
  drugCode: string;
  stockLevels: StockLevel[];
}

const DEFAULT_FORM: ReorderConfig = {
  drug_code: "",
  site_code: "",
  min_stock: 10,
  reorder_point: 25,
  max_stock: 80,
  reorder_lead_days: 7,
  is_active: true,
};

export function ReorderConfigForm({ drugCode, stockLevels }: ReorderConfigFormProps) {
  const { success, error: showError } = useToast();
  const [siteCode, setSiteCode] = useState("");
  const [form, setForm] = useState<ReorderConfig>(DEFAULT_FORM);
  const [isSaving, setIsSaving] = useState(false);

  const selectedStock = stockLevels.find((item) => item.site_code === siteCode) ?? stockLevels[0];
  const { data, error, isLoading, saveConfig } = useReorderConfig({
    drug_code: drugCode,
    site_code: siteCode || selectedStock?.site_code,
  });

  useEffect(() => {
    if (!siteCode && stockLevels[0]?.site_code) {
      setSiteCode(stockLevels[0].site_code);
    }
  }, [siteCode, stockLevels]);

  useEffect(() => {
    if (!selectedStock) return;

    if (data) {
      setForm({
        ...data,
        drug_code: data.drug_code,
        site_code: data.site_code,
      });
      return;
    }

    const baseline = Math.max(1, Math.round(selectedStock.current_quantity));
    setForm({
      ...DEFAULT_FORM,
      drug_code: drugCode,
      site_code: selectedStock.site_code,
      min_stock: Math.max(5, Math.round(baseline * 0.25)),
      reorder_point: Math.max(10, Math.round(baseline * 0.5)),
      max_stock: Math.max(20, Math.round(baseline * 1.5)),
    });
  }, [data, drugCode, selectedStock]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!siteCode) return;

    setIsSaving(true);
    try {
      await saveConfig({
        ...form,
        drug_code: drugCode,
        site_code: siteCode,
      });
      success("Reorder configuration saved");
    } catch (saveError) {
      showError(saveError instanceof Error ? saveError.message : "Failed to save reorder configuration");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="viz-panel rounded-[1.75rem] p-5">
      <div className="mb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
          Reorder Configuration
        </p>
        <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
          Thresholds & lead times
        </h3>
      </div>

      {!stockLevels.length ? (
        <p className="rounded-2xl border border-dashed border-border/70 px-4 py-6 text-sm text-text-secondary">
          Stock must be available for at least one site before reorder settings can be configured.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Site
            </span>
            <select
              value={siteCode}
              onChange={(event) => setSiteCode(event.target.value)}
              className="h-11 w-full rounded-2xl border border-border bg-page px-4 text-sm text-text-primary outline-none transition-colors focus:border-accent focus:ring-1 focus:ring-accent"
            >
              {stockLevels.map((item) => (
                <option key={item.site_code} value={item.site_code}>
                  {item.site_name} ({item.site_code})
                </option>
              ))}
            </select>
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            {[
              { key: "min_stock", label: "Minimum stock" },
              { key: "reorder_point", label: "Reorder point" },
              { key: "max_stock", label: "Maximum stock" },
              { key: "reorder_lead_days", label: "Lead days" },
            ].map((field) => (
              <label key={field.key} className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
                  {field.label}
                </span>
                <input
                  type="number"
                  min={0}
                  value={form[field.key as keyof ReorderConfig] as number}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      [field.key]: Number(event.target.value),
                    }))
                  }
                  className="h-11 w-full rounded-2xl border border-border bg-page px-4 text-sm text-text-primary outline-none transition-colors focus:border-accent focus:ring-1 focus:ring-accent"
                />
              </label>
            ))}
          </div>

          <label className="flex items-center gap-3 rounded-2xl border border-border/70 px-4 py-3">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  is_active: event.target.checked,
                }))
              }
              className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
            />
            <div>
              <p className="font-medium text-text-primary">Configuration active</p>
              <p className="text-sm text-text-secondary">
                Alerts and reorder calculations will use these thresholds.
              </p>
            </div>
          </label>

          {error && !isLoading && (
            <p className={cn("rounded-2xl border px-4 py-3 text-sm", "border-chart-amber/40 bg-chart-amber/10 text-chart-amber")}>
              Existing reorder settings could not be loaded. You can still save a new configuration.
            </p>
          )}

          <div className="flex items-center justify-between">
            <p className="text-sm text-text-secondary">
              Current on-hand quantity: {selectedStock ? selectedStock.current_quantity : 0}
            </p>
            <Button type="submit" loading={isSaving}>
              Save configuration
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
