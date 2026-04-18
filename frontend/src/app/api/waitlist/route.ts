import { NextResponse } from "next/server";

const DATAPULSE_API = process.env.DATAPULSE_API_URL ?? "http://api:8000";

// In-process rate limiter retained as a first-pass guard.
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 5;
const RATE_WINDOW = 60 * 60 * 1000;

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW });
    return false;
  }
  entry.count++;
  return entry.count > RATE_LIMIT;
}

export async function POST(request: Request) {
  try {
    const forwarded = request.headers.get("x-forwarded-for");
    const ip = forwarded?.split(",").map((s) => s.trim()).filter(Boolean).at(-1) ?? "unknown";

    if (isRateLimited(ip)) {
      return NextResponse.json(
        { success: false, message: "Too many requests. Please try again later." },
        { status: 429 },
      );
    }

    const body = await request.json();
    const email = body?.email?.trim()?.toLowerCase();

    if (!email || !/^[a-zA-Z0-9._\-+]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email)) {
      return NextResponse.json(
        { success: false, message: "Please provide a valid email address." },
        { status: 400 },
      );
    }

    const upstream = await fetch(`${DATAPULSE_API}/api/v1/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        name: body?.name ?? null,
        company: body?.company ?? null,
        use_case: body?.use_case ?? null,
        team_size: body?.team_size ?? null,
        tier: body?.tier ?? null,
      }),
    });

    const data = await upstream.json().catch(() => ({}));

    if (!upstream.ok) {
      return NextResponse.json(
        { success: false, message: data.message ?? "Something went wrong." },
        { status: upstream.status },
      );
    }

    return NextResponse.json({ success: true, message: data.message });
  } catch {
    return NextResponse.json(
      { success: false, message: "Something went wrong. Please try again." },
      { status: 500 },
    );
  }
}
