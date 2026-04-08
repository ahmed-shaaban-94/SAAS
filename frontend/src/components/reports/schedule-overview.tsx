"use client";

import { useState } from "react";
import { useReportSchedules } from "@/hooks/use-report-schedules";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { Plus, Clock, Trash2, ToggleLeft, ToggleRight } from "lucide-react";

const CRON_PRESETS = [
  { label: "Daily at 8am", value: "0 8 * * *" },
  { label: "Weekly (Monday)", value: "0 8 * * 1" },
  { label: "Monthly (1st)", value: "0 8 1 * *" },
];

export function ScheduleOverview() {
  const { schedules, isLoading, error, createSchedule, toggleSchedule, deleteSchedule } =
    useReportSchedules();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [reportType, setReportType] = useState("dashboard");
  const [cron, setCron] = useState("0 8 * * 1");
  const [recipients, setRecipients] = useState("");

  if (isLoading && schedules.length === 0) return <LoadingCard className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load schedules" />;

  const handleCreate = async () => {
    if (!name) return;
    await createSchedule({
      name,
      report_type: reportType,
      cron_expression: cron,
      recipients: recipients.split(",").map((e) => e.trim()).filter(Boolean),
    });
    setShowForm(false);
    setName("");
    setRecipients("");
  };

  return (
    <div className="space-y-4 mt-6">
      <button
        onClick={() => setShowForm(!showForm)}
        className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
      >
        <Plus className="h-4 w-4" /> New Schedule
      </button>

      {showForm && (
        <div className="rounded-xl border border-accent/30 bg-accent/5 p-4 space-y-3">
          <input
            placeholder="Schedule name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary"
          />
          <div className="flex gap-2">
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary"
            >
              {["dashboard", "products", "customers", "staff"].map((t) => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
            <select
              value={cron}
              onChange={(e) => setCron(e.target.value)}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary"
            >
              {CRON_PRESETS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
          <input
            placeholder="Recipient emails (comma-separated)"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary"
          />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white">
              Create
            </button>
            <button onClick={() => setShowForm(false)} className="rounded-lg px-4 py-2 text-sm text-text-secondary hover:bg-divider">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Schedule list */}
      <div className="space-y-2">
        {schedules.map((s) => (
          <div key={s.id} className="flex items-center gap-3 rounded-xl border border-border bg-card p-4">
            <Clock className="h-4 w-4 text-text-secondary flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary">{s.name}</p>
              <p className="text-xs text-text-secondary">
                {s.report_type} &middot; <code className="font-mono">{s.cron_expression}</code>
                {s.recipients.length > 0 && ` &middot; ${s.recipients.join(", ")}`}
              </p>
              {s.last_run_at && (
                <p className="text-[10px] text-text-tertiary">
                  Last run: {new Date(s.last_run_at).toLocaleString()}
                </p>
              )}
            </div>
            <button
              onClick={() => toggleSchedule(s.id, !s.enabled)}
              className="text-text-secondary hover:text-accent"
              title={s.enabled ? "Disable" : "Enable"}
            >
              {s.enabled ? (
                <ToggleRight className="h-5 w-5 text-green-500" />
              ) : (
                <ToggleLeft className="h-5 w-5 text-text-tertiary" />
              )}
            </button>
            <button
              onClick={() => deleteSchedule(s.id)}
              className="text-text-secondary hover:text-red-500"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        {schedules.length === 0 && (
          <div className="rounded-xl border border-border bg-card p-8 text-center text-text-tertiary">
            No report schedules configured
          </div>
        )}
      </div>
    </div>
  );
}
