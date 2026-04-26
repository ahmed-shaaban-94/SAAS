import { StyleSheet, Text, View } from "react-native";

import { colors, spacing } from "../theme/tokens";

interface MetricCardProps {
  label: string;
  value: string;
  caption?: string;
  tone?: "accent" | "success" | "warning";
}

export function MetricCard({
  label,
  value,
  caption,
  tone = "accent",
}: MetricCardProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, toneStyles[tone]]}>{value}</Text>
      {caption ? <Text style={styles.caption}>{caption}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexBasis: "48%",
    backgroundColor: colors.surfaceAlt,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    minHeight: 116,
  },
  label: {
    color: colors.textMuted,
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.9,
  },
  value: {
    marginTop: spacing.sm,
    fontSize: 24,
    fontWeight: "700",
  },
  caption: {
    marginTop: spacing.sm,
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 16,
  },
});

const toneStyles = StyleSheet.create({
  accent: {
    color: colors.accent,
  },
  success: {
    color: colors.success,
  },
  warning: {
    color: colors.warning,
  },
});
