/** Supported locales and default locale for the app. */
export const locales = ["en", "ar"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

/** RTL languages. */
export const rtlLocales = new Set<Locale>(["ar"]);

export function isRtl(locale: Locale): boolean {
  return rtlLocales.has(locale);
}
