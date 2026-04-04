import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { locales } from "@/i18n/config";

/**
 * POST /api/locale — Set the NEXT_LOCALE cookie.
 *
 * Body: { "locale": "en" | "ar" }
 */
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const locale = body.locale as string;

  if (!locale || !(locales as readonly string[]).includes(locale)) {
    return NextResponse.json(
      { error: "Invalid locale. Supported: " + locales.join(", ") },
      { status: 400 },
    );
  }

  const response = NextResponse.json({ locale });
  response.cookies.set("NEXT_LOCALE", locale, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365, // 1 year
    sameSite: "lax",
  });

  return response;
}
