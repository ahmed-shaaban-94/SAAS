"use client";

import { useEffect, useState } from "react";

/** Late-refill entry surfaced in the churn alert. */
export interface PosLateRefill {
  drug_name: string;
  days_late: number;
}

/** Churn info block on the customer lookup response. */
export interface PosCustomerChurnInfo {
  risk: boolean;
  last_refill_due: string | null;
  late_refills: PosLateRefill[];
}

/**
 * Frontend-side view of the (yet-to-be-built) customer-lookup endpoint.
 *
 * Contract tracked in issue #624 — once the backend lands
 * `GET /api/v1/pos/customers/by-phone/{phone}`, the fixture branch
 * in {@link usePosCustomerLookup} flips to a real `fetchAPI` call
 * and nothing else in the UI needs to change.
 */
export interface PosCustomerLookup {
  customer_key: number;
  customer_name: string;
  phone: string;
  loyalty_points: number;
  loyalty_tier: "VIP" | "REGULAR" | null;
  vip_since: string | null;
  outstanding_credit_egp: number;
  churn: PosCustomerChurnInfo;
}

interface LookupState {
  data: PosCustomerLookup | null;
  isLoading: boolean;
  error: string | null;
}

const INITIAL: LookupState = { data: null, isLoading: false, error: null };

/** Egyptian mobile — accepts `01xxxxxxxxx` (11 digits) or `+20...` / `20...`.
 *  Normalizes to E.164 `+20xxxxxxxxxx`. Returns null for unparseable input. */
export function normalizeEgyptianPhone(raw: string): string | null {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 0) return null;
  if (digits.startsWith("20") && digits.length === 12) return `+${digits}`;
  if (digits.startsWith("0") && digits.length === 11) return `+2${digits}`;
  if (digits.length === 10 && digits.startsWith("1")) return `+20${digits}`;
  return null;
}

/** Dev fixture — flip on via localStorage key `pos:d3_fixture` = "vip-churn"
 *  or "vip-healthy" or "walkin". Anything else (or unset) = no fixture, real
 *  fetch is attempted. Documented on issue #624. */
type FixtureKey = "vip-churn" | "vip-healthy" | "walkin";

const FIXTURES: Record<FixtureKey, PosCustomerLookup> = {
  "vip-churn": {
    customer_key: 101,
    customer_name: "أستاذة منى",
    phone: "+201198765432",
    loyalty_points: 300,
    loyalty_tier: "VIP",
    vip_since: "2023-04-01",
    outstanding_credit_egp: 0,
    churn: {
      risk: true,
      last_refill_due: "2026-04-16",
      late_refills: [{ drug_name: "كونكور 5 ملجم", days_late: 6 }],
    },
  },
  "vip-healthy": {
    customer_key: 102,
    customer_name: "مهندس خالد",
    phone: "+201012345678",
    loyalty_points: 1250,
    loyalty_tier: "VIP",
    vip_since: "2022-11-15",
    outstanding_credit_egp: -450,
    churn: { risk: false, last_refill_due: null, late_refills: [] },
  },
  walkin: {
    customer_key: 999,
    customer_name: "عميل جديد",
    phone: "+201005550001",
    loyalty_points: 0,
    loyalty_tier: null,
    vip_since: null,
    outstanding_credit_egp: 0,
    churn: { risk: false, last_refill_due: null, late_refills: [] },
  },
};

function readFixtureKey(): FixtureKey | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem("pos:d3_fixture");
    if (raw === "vip-churn" || raw === "vip-healthy" || raw === "walkin") {
      return raw;
    }
  } catch {
    // localStorage unavailable — fall through
  }
  return null;
}

/**
 * Look up a customer by phone. Debounces input ~300ms.
 *
 * Returns `{ data, isLoading, error }`. When the backend does not
 * (yet) know the number we return `{ data: null, error: null }` — a
 * benign "new walk-in" state, NOT an error toast.
 *
 * TODO(issue #624): replace the fixture branch with
 * `fetchAPI<PosCustomerLookup>('/api/v1/pos/customers/by-phone/' + normalized)`.
 */
export function usePosCustomerLookup(rawPhone: string): LookupState {
  const [state, setState] = useState<LookupState>(INITIAL);

  useEffect(() => {
    const normalized = normalizeEgyptianPhone(rawPhone);
    if (!normalized) {
      setState(INITIAL);
      return;
    }
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    const timer = setTimeout(() => {
      const fixtureKey = readFixtureKey();
      if (fixtureKey) {
        const fixture = FIXTURES[fixtureKey];
        // Override phone on fixture so the UI reflects the typed number,
        // not the canned fixture number. Keeps demo coherent.
        setState({
          data: { ...fixture, phone: normalized },
          isLoading: false,
          error: null,
        });
        return;
      }
      // No fixture set → live lookup. Backend endpoint is not built
      // yet (issue #624), so we return null (benign "unknown number"
      // state) rather than surface a 404 to the cashier.
      setState({ data: null, isLoading: false, error: null });
    }, 300);
    return () => clearTimeout(timer);
  }, [rawPhone]);

  return state;
}
