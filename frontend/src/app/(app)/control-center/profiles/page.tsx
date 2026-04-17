"use client";

import { useState } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { useProfiles, createProfile, updateProfile, type PipelineProfile } from "@/hooks/use-profiles";
import { Plus, SlidersHorizontal, X } from "lucide-react";

function ProfileForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial: PipelineProfile | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [displayName, setDisplayName] = useState(initial?.display_name ?? "");
  const [profileKey, setProfileKey] = useState(initial?.profile_key ?? "");
  const [targetDomain, setTargetDomain] = useState(initial?.target_domain ?? "sales_orders");
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const domains = ["sales_orders", "inventory_snapshot", "products", "customers", "sites"];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (initial) {
        await updateProfile(initial.id, { display_name: displayName, is_default: isDefault });
      } else {
        await createProfile({ profile_key: profileKey, display_name: displayName, target_domain: targetDomain, is_default: isDefault });
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mb-6 rounded-2xl border border-border/50 bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold text-text-primary">{initial ? "Edit Profile" : "New Pipeline Profile"}</h3>
        <button onClick={onCancel}><X className="h-4 w-4 text-text-secondary" /></button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        {!initial && (
          <>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-primary">Profile Key</label>
              <input
                type="text"
                value={profileKey}
                onChange={(e) => setProfileKey(e.target.value)}
                required
                placeholder="e.g. default-sales"
                className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-primary">Target Domain</label>
              <select
                value={targetDomain}
                onChange={(e) => setTargetDomain(e.target.value)}
                className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary"
              >
                {domains.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          </>
        )}
        <div>
          <label className="mb-1 block text-sm font-medium text-text-primary">Display Name</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            className="w-full rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary"
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id="is-default"
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            className="h-4 w-4"
          />
          <label htmlFor="is-default" className="text-sm text-text-primary">Set as default profile</label>
        </div>
        {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="rounded-xl border border-border/70 px-4 py-2 text-sm text-text-secondary">Cancel</button>
          <button type="submit" disabled={saving} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60">
            {saving ? "Saving…" : initial ? "Save Changes" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function ProfilesPage() {
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<PipelineProfile | null>(null);
  const { data, isLoading, error, mutate } = useProfiles({ page, page_size: 25 });
  const totalPages = Math.ceil(data.total / 25);

  if (isLoading && !data.items.length) return <LoadingCard className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load profiles" />;

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Pipeline Profiles"
        description="Processing profiles targeting canonical data domains"
        action={
          <button
            onClick={() => { setEditing(null); setShowForm(true); }}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> New Profile
          </button>
        }
      />

      {showForm && (
        <ProfileForm initial={editing} onSaved={() => { setShowForm(false); mutate(); }} onCancel={() => setShowForm(false)} />
      )}

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.items.map((profile) => (
          <div key={profile.id} className="rounded-2xl border border-border/50 bg-card p-5 space-y-2">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-5 w-5 text-primary" />
                <span className="font-semibold text-text-primary">{profile.display_name}</span>
              </div>
              {profile.is_default && (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">default</span>
              )}
            </div>
            <p className="text-xs font-mono text-text-secondary">{profile.profile_key}</p>
            <p className="text-xs text-text-secondary">Domain: <strong className="text-text-primary">{profile.target_domain}</strong></p>
            <div className="flex justify-end">
              <button
                onClick={() => { setEditing(profile); setShowForm(true); }}
                className="text-xs text-text-secondary hover:text-text-primary"
              >
                Edit
              </button>
            </div>
          </div>
        ))}
        {data.items.length === 0 && (
          <p className="col-span-full py-12 text-center text-text-secondary">No profiles yet.</p>
        )}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary disabled:opacity-40">Previous</button>
          <span className="px-3 py-1.5 text-sm text-text-secondary">{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary disabled:opacity-40">Next</button>
        </div>
      )}
    </PageTransition>
  );
}
