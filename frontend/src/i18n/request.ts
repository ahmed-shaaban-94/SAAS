import { getRequestConfig } from "next-intl/server";
import { cookies, headers } from "next/headers";
import { defaultLocale, locales, type Locale } from "./config";

/**
 * Resolve the locale for the current request.
 *
 * Priority: NEXT_LOCALE cookie > Accept-Language header > default ("en").
 */
async function resolveLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get("NEXT_LOCALE")?.value;
  if (cookieLocale && (locales as readonly string[]).includes(cookieLocale)) {
    return cookieLocale as Locale;
  }

  // Peek at Accept-Language for a best-effort match
  const headerStore = await headers();
  const acceptLang = headerStore.get("accept-language") ?? "";
  for (const locale of locales) {
    if (acceptLang.includes(locale)) return locale;
  }

  return defaultLocale;
}

export default getRequestConfig(async () => {
  const locale = await resolveLocale();

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
