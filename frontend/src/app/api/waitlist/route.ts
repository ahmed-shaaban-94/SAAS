import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const WAITLIST_PATH = path.join(process.cwd(), "waitlist.json");

// Simple in-memory rate limiter
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 5; // max requests
const RATE_WINDOW = 60 * 60 * 1000; // 1 hour

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

async function readWaitlist(): Promise<string[]> {
  try {
    const data = await fs.readFile(WAITLIST_PATH, "utf-8");
    return JSON.parse(data);
  } catch {
    return [];
  }
}

async function writeWaitlist(emails: string[]): Promise<void> {
  await fs.writeFile(WAITLIST_PATH, JSON.stringify(emails, null, 2));
}

export async function POST(request: Request) {
  try {
    // Rate limiting — use rightmost X-Forwarded-For entry (closest trusted proxy)
    // to prevent spoofing via client-injected headers.
    // Falls back to "unknown" if no proxy header is present.
    const forwarded = request.headers.get("x-forwarded-for");
    const forwardedParts = forwarded?.split(",").map((s) => s.trim()).filter(Boolean);
    const ip = forwardedParts?.at(-1) || "unknown";

    if (isRateLimited(ip)) {
      return NextResponse.json(
        { success: false, message: "Too many requests. Please try again later." },
        { status: 429 }
      );
    }

    // Parse & validate
    const body = await request.json();
    const email = body?.email?.trim()?.toLowerCase();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json(
        { success: false, message: "Please provide a valid email address." },
        { status: 400 }
      );
    }

    // Store
    const waitlist = await readWaitlist();

    if (waitlist.includes(email)) {
      return NextResponse.json({
        success: true,
        message: "You're already on the list!",
      });
    }

    waitlist.push(email);
    await writeWaitlist(waitlist);

    return NextResponse.json({
      success: true,
      message: "You're on the list! We'll be in touch soon.",
    });
  } catch {
    return NextResponse.json(
      { success: false, message: "Something went wrong. Please try again." },
      { status: 500 }
    );
  }
}
