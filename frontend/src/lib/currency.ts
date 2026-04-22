/**
 * Format a price in its minor unit (USD cents or EGP piastres) for display.
 *
 * The backend stores plan prices in minor units (see `PlanLimits.price_egp`)
 * to avoid float rounding and to map cleanly onto provider cents APIs.
 * This helper is the ONLY place the frontend divides by 100.
 */
export function formatPrice(
  minorUnits: number,
  currency: string,
  locale: string,
): string {
  const major = minorUnits / 100;
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(major);
  } catch {
    // Unknown currency → render as "<code> <amount>"
    return `${currency} ${major.toFixed(2)}`;
  }
}
