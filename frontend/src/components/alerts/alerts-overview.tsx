"use client";

import { useAlertLog } from "@/hooks/use-alerts";
import { formatCurrency } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { Bell, BellOff, Check, AlertTriangle, Info, XCircle } from "lucide-react";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const SEVERITY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  critical: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-500 bg-red-500/10 border-red-500/20",
  warning: "text-yellow-500 bg-yellow-500/10 border-yellow-500/20",
  info: "text-blue-500 bg-blue-500/10 border-blue-500/20",
};

export function AlertsOverview() {
  const { data: allAlerts, isLoading, error, acknowledgeAlert } = useAlertLog(false);
  const unacknowledged = allAlerts?.filter((a) => !a.acknowledged) ?? [];
  const acknowledged = allAlerts?.filter((a) => a.acknowledged) ?? [];

  if (isLoading) return <LoadingCard className="h-96" />;
  if (error) return <ErrorRetry title="Failed to load alerts" />;

  return (
    <div className="mt-6 space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="viz-panel viz-card-hover rounded-[1.5rem] p-5">
          <Bell className="mb-3 h-4 w-4 text-accent" />
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Total Alerts</p>
          <p className="text-2xl font-bold text-text-primary">{allAlerts?.length ?? 0}</p>
        </div>
        <div className="viz-panel rounded-[1.5rem] border-red-500/20 bg-red-500/8 p-5">
          <AlertTriangle className="mb-3 h-4 w-4 text-red-500" />
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Unacknowledged</p>
          <p className="text-2xl font-bold text-red-500">{unacknowledged.length}</p>
        </div>
        <div className="viz-panel rounded-[1.5rem] border-green-500/20 bg-green-500/8 p-5">
          <Check className="mb-3 h-4 w-4 text-green-500" />
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Acknowledged</p>
          <p className="text-2xl font-bold text-green-500">{acknowledged.length}</p>
        </div>
      </div>

      {unacknowledged.length > 0 && (
        <div className="viz-panel rounded-[1.75rem] p-5">
          <h3 className="mb-4 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            <Bell className="h-4 w-4 text-accent" />
            Active Alerts
          </h3>
          <div className="space-y-3">
            {unacknowledged.map((alert) => {
              const severity = alert.message?.includes("critical") ? "critical" : "warning";
              const Icon = SEVERITY_ICONS[severity] ?? AlertTriangle;
              return (
                <div key={alert.id} className={`flex items-center gap-3 rounded-[1.25rem] border p-4 ${SEVERITY_COLORS[severity]}`}>
                  <Icon className="h-5 w-5 flex-shrink-0" aria-label={`${severity} severity`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{alert.alert_name || alert.message || "Alert"}</p>
                    {alert.message && <p className="text-xs opacity-80 mt-0.5">{alert.message}</p>}
                    <p className="text-[10px] opacity-60 mt-0.5">{timeAgo(alert.fired_at)}</p>
                  </div>
                  <button
                    onClick={() => acknowledgeAlert(alert.id)}
                    className="viz-panel-soft flex-shrink-0 rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-primary transition-colors hover:text-accent"
                  >
                    Acknowledge
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="viz-panel rounded-[1.75rem] p-5">
        <h3 className="mb-4 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
          <BellOff className="h-4 w-4 text-text-secondary" />
          Alert History
        </h3>
        {(!allAlerts || allAlerts.length === 0) ? (
          <div className="text-center py-8">
            <Bell className="h-10 w-10 text-text-secondary mx-auto mb-2 opacity-30" />
            <p className="text-sm text-text-secondary">No alerts yet</p>
            <p className="text-xs text-text-secondary mt-1">Alerts will appear here when metric thresholds are breached</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {allAlerts.map((alert) => (
              <div key={alert.id} className={`flex items-center gap-3 rounded-[1.15rem] px-3 py-3 text-sm transition-colors ${alert.acknowledged ? "opacity-60" : ""} hover:bg-background/50`}>
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${alert.acknowledged ? "bg-gray-400" : "bg-red-500"}`} />
                <span className="text-text-primary flex-1 truncate">{alert.alert_name || alert.message || "Alert"}</span>
                {alert.metric_value !== null && (
                  <span className="text-xs text-text-secondary">{formatCurrency(alert.metric_value)}</span>
                )}
                <span className="text-xs text-text-secondary flex-shrink-0">{timeAgo(alert.fired_at)}</span>
                {alert.acknowledged && <Check className="h-3 w-3 text-green-500 flex-shrink-0" />}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
