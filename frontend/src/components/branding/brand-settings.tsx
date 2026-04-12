"use client";

import { useState } from "react";
import { useBranding, type BrandingConfig } from "@/hooks/use-branding";
import { API_BASE_URL } from "@/lib/constants";
import { LoadingCard } from "@/components/loading-card";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Save, RotateCcw } from "lucide-react";

async function updateBranding(data: Partial<BrandingConfig>): Promise<BrandingConfig> {
  const res = await fetch(`${API_BASE_URL}/api/v1/branding/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err);
  }
  return res.json();
}

export function BrandSettings() {
  const { data: branding, isLoading, mutate } = useBranding();
  const { success, error: toastError } = useToast();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<BrandingConfig>>({});

  if (isLoading || !branding) return <LoadingCard lines={8} />;

  const merged = { ...branding, ...form };

  const handleChange = (key: keyof BrandingConfig, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setError(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateBranding(form);
      mutate(updated, false);
      setForm({});
      success("Branding settings saved");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save";
      setError(msg);
      toastError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setForm({});
    setError(null);
  };

  const hasChanges = Object.keys(form).length > 0;

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Identity */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-text-primary">Identity</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-xs text-text-secondary">Company Name</span>
            <input
              type="text"
              value={merged.company_name}
              onChange={(e) => handleChange("company_name", e.target.value)}
              className="w-full rounded-lg border border-border bg-bg-page px-3 py-2 text-sm text-text-primary"
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs text-text-secondary">Subdomain</span>
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={merged.subdomain || ""}
                onChange={(e) => handleChange("subdomain", e.target.value)}
                placeholder="your-company"
                className="w-full rounded-lg border border-border bg-bg-page px-3 py-2 text-sm text-text-primary"
              />
              <span className="text-xs text-text-secondary whitespace-nowrap">.datapulse.tech</span>
            </div>
          </label>
        </div>
      </section>

      {/* Colors */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-text-primary">Colors</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          {(["primary_color", "accent_color", "sidebar_bg"] as const).map((key) => (
            <label key={key} className="space-y-1">
              <span className="text-xs text-text-secondary capitalize">
                {key.replace(/_/g, " ")}
              </span>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={(merged[key] as string) || "#000000"}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="h-8 w-8 cursor-pointer rounded border border-border"
                />
                <input
                  type="text"
                  value={(merged[key] as string) || ""}
                  onChange={(e) => handleChange(key, e.target.value)}
                  placeholder="#000000"
                  className="w-full rounded-lg border border-border bg-bg-page px-3 py-2 text-sm text-text-primary font-mono"
                />
              </div>
            </label>
          ))}
        </div>
      </section>

      {/* White-label */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-text-primary">White-Label</h3>
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={merged.hide_datapulse_branding}
            onChange={(e) => handleChange("hide_datapulse_branding", e.target.checked)}
            className="h-4 w-4 rounded border-border accent-accent"
          />
          <span className="text-sm text-text-primary">Hide DataPulse branding</span>
        </label>
        <label className="space-y-1">
          <span className="text-xs text-text-secondary">Custom Domain</span>
          <input
            type="text"
            value={merged.custom_domain || ""}
            onChange={(e) => handleChange("custom_domain", e.target.value)}
            placeholder="analytics.yourcompany.com"
            className="w-full rounded-lg border border-border bg-bg-page px-3 py-2 text-sm text-text-primary"
          />
        </label>
      </section>

      {/* Support */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-text-primary">Support & Footer</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-xs text-text-secondary">Support Email</span>
            <input
              type="email"
              value={merged.support_email || ""}
              onChange={(e) => handleChange("support_email", e.target.value)}
              className="w-full rounded-lg border border-border bg-bg-page px-3 py-2 text-sm text-text-primary"
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs text-text-secondary">Footer Text</span>
            <input
              type="text"
              value={merged.footer_text || ""}
              onChange={(e) => handleChange("footer_text", e.target.value)}
              className="w-full rounded-lg border border-border bg-bg-page px-3 py-2 text-sm text-text-primary"
            />
          </label>
        </div>
      </section>

      {/* Actions */}
      {hasChanges && (
        <div className="flex items-center justify-end gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
          >
            <RotateCcw className="h-4 w-4" /> Reset
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            loading={saving}
          >
            <Save className="h-4 w-4" /> Save Changes
          </Button>
        </div>
      )}
    </div>
  );
}
