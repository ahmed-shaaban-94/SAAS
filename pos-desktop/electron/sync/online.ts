/**
 * Online detection via periodic HEAD /health ping (§6.3).
 *
 * State machine: online → degraded (1 failure) → offline (3 failures) → online (1 success).
 * This prevents flapping on transient packet loss.
 */

const PING_TIMEOUT_MS = 5_000;
const OFFLINE_THRESHOLD = 3; // consecutive failures before declaring offline

let _failureCount = 0;
let _online = false;

export function isOnline(): boolean {
  return _online;
}

/**
 * Send a HEAD /health ping and update the internal online state machine.
 * Returns the new online status.
 */
export async function checkOnline(baseUrl: string): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), PING_TIMEOUT_MS);

    const res = await fetch(`${baseUrl}/health`, {
      method: "HEAD",
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (res.ok || res.status < 500) {
      _failureCount = 0;
      _online = true;
    } else {
      _failureCount++;
      if (_failureCount >= OFFLINE_THRESHOLD) _online = false;
    }
  } catch {
    _failureCount++;
    if (_failureCount >= OFFLINE_THRESHOLD) _online = false;
  }

  return _online;
}

/** Reset state (used in tests). */
export function resetOnlineState(): void {
  _failureCount = 0;
  _online = false;
}
