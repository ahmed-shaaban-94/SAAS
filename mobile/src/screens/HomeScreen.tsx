import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import { env } from "../config/env";
import { useDashboardBootstrap } from "../hooks/useDashboardBootstrap";
import { colors, spacing } from "../theme/tokens";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

export function HomeScreen() {
  const {
    health,
    summary,
    healthError,
    summaryError,
    summaryState,
    loading,
    refreshing,
    lastUpdated,
    refresh,
  } = useDashboardBootstrap();

  return (
    <ScrollView
      style={styles.scrollView}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void refresh()} />}
    >
      <View style={styles.hero}>
        <Text style={styles.eyebrow}>Expo + React Native Foundation</Text>
        <Text style={styles.title}>{env.appName}</Text>
        <Text style={styles.subtitle}>
          DataPulse mobile now starts from a React stack, not Flutter. This starter is wired to the
          existing backend and ready for shared contracts, auth, and navigation next.
        </Text>

        <View style={styles.pillRow}>
          <View style={styles.pill}>
            <Text style={styles.pillText}>
              {env.apiUrl ? `API: ${env.apiUrl}` : "API URL not configured"}
            </Text>
          </View>
          <View style={styles.pill}>
            <Text style={styles.pillText}>
              {env.apiKey ? "Dev API key enabled" : "Auth bridge pending"}
            </Text>
          </View>
        </View>
      </View>

      <SectionCard
        title="Platform stance"
        subtitle="This is the mobile starting point I recommend for DataPulse."
      >
        <View style={styles.bulletList}>
          <Text style={styles.bullet}>Next.js stays the primary web surface.</Text>
          <Text style={styles.bullet}>Expo React Native becomes the mobile app path.</Text>
          <Text style={styles.bullet}>Flutter is no longer part of the forward build strategy.</Text>
          <Text style={styles.bullet}>Shared API contracts should be the next multiplier.</Text>
        </View>
      </SectionCard>

      <SectionCard
        title="System health"
        subtitle="Pulled from `/health/ready` to confirm the app can reach the backend."
      >
        {loading && !health ? (
          <View style={styles.loadingState}>
            <ActivityIndicator color={colors.accent} />
            <Text style={styles.muted}>Checking backend readiness…</Text>
          </View>
        ) : health ? (
          <View style={styles.healthGrid}>
            <MetricCard
              label="API"
              value={health.status === "ok" ? "Ready" : "Degraded"}
              tone={health.status === "ok" ? "success" : "warning"}
              caption="FastAPI readiness endpoint"
            />
            <MetricCard
              label="Database"
              value={health.db === "connected" ? "Connected" : "Disconnected"}
              tone={health.db === "connected" ? "success" : "warning"}
              caption="Database dependency health"
            />
          </View>
        ) : (
          <Text style={styles.errorText}>{healthError || "Unable to reach the backend."}</Text>
        )}
      </SectionCard>

      <SectionCard
        title="Dashboard bootstrap"
        subtitle="Pulled from `/api/v1/analytics/summary`. This shows where mobile auth or shared contracts slot in next."
      >
        {loading && !summary ? (
          <View style={styles.loadingState}>
            <ActivityIndicator color={colors.accent} />
            <Text style={styles.muted}>Loading summary…</Text>
          </View>
        ) : summary ? (
          <View style={styles.metricGrid}>
            <MetricCard
              label="Period gross"
              value={formatNumber(summary.period_gross)}
              caption="Primary KPI alias used by new surfaces"
            />
            <MetricCard
              label="Transactions"
              value={formatNumber(summary.period_transactions)}
              caption="Period-aware transaction count"
              tone="success"
            />
            <MetricCard
              label="Customers"
              value={formatNumber(summary.period_customers)}
              caption="Period-aware customer count"
            />
            <MetricCard
              label="MoM growth"
              value={formatPercent(summary.mom_growth_pct)}
              caption="Month-over-month gross sales movement"
              tone="warning"
            />
          </View>
        ) : (
          <View style={styles.bulletList}>
            <Text style={styles.bullet}>
              {summaryState === "auth_required"
                ? "Summary is protected. Add mobile JWT auth or use a dev-only EXPO_PUBLIC_API_KEY."
                : summaryError || "Summary endpoint is not available yet."}
            </Text>
            <Text style={styles.bullet}>
              The app scaffold is still useful now because the typed API layer and mobile shell are in place.
            </Text>
          </View>
        )}
      </SectionCard>

      <SectionCard
        title="Next build steps"
        subtitle="The foundation is intentionally lean so we can harden the right seams next."
      >
        <View style={styles.bulletList}>
          <Text style={styles.bullet}>Add React Navigation or Expo Router once the screen map is agreed.</Text>
          <Text style={styles.bullet}>Move auth/session handling onto the same canonical provider as web.</Text>
          <Text style={styles.bullet}>Generate shared API contracts so web and mobile stop duplicating DTOs.</Text>
          <Text style={styles.bullet}>Port the upload, dashboard, and alerts flows first because they maximize product value.</Text>
        </View>
      </SectionCard>

      <Text style={styles.footer}>
        {lastUpdated ? `Last refresh: ${new Date(lastUpdated).toLocaleString()}` : "Waiting for first refresh"}
      </Text>
    </ScrollView>
  );
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }

  return currencyFormatter.format(value);
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${percentFormatter.format(value)}%`;
}

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
    gap: spacing.md,
  },
  hero: {
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  eyebrow: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  title: {
    marginTop: spacing.sm,
    color: colors.text,
    fontSize: 34,
    fontWeight: "800",
    lineHeight: 38,
  },
  subtitle: {
    marginTop: spacing.sm,
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 22,
    maxWidth: 560,
  },
  pillRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  pill: {
    backgroundColor: colors.pill,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  pillText: {
    color: colors.text,
    fontSize: 12,
    fontWeight: "600",
  },
  bulletList: {
    gap: spacing.sm,
  },
  bullet: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20,
  },
  healthGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },
  metricGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },
  loadingState: {
    alignItems: "flex-start",
    gap: spacing.sm,
  },
  muted: {
    color: colors.textMuted,
    fontSize: 14,
  },
  errorText: {
    color: colors.danger,
    fontSize: 14,
    lineHeight: 20,
  },
  footer: {
    color: colors.textMuted,
    fontSize: 12,
    textAlign: "center",
    marginTop: spacing.sm,
  },
});
