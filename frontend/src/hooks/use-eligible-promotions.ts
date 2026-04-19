import { useEffect, useState } from "react";
import { postAPI } from "@/lib/api-client";
import type {
  EligiblePromotionsRequest,
  EligiblePromotionsResponse,
} from "@/types/promotions";

/**
 * Fetch eligible promotions for the current cart state. This is a POST
 * (not SWR GET) because the cart body is the cache key and evolves with
 * every add/remove. Re-fires on each `enabled` flip — callers typically
 * gate it behind modal-open state to avoid thrashing the endpoint.
 */
export function useEligiblePromotions(
  request: EligiblePromotionsRequest | null,
  enabled: boolean,
) {
  const [data, setData] = useState<EligiblePromotionsResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!enabled || !request || request.items.length === 0) {
      setData(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    postAPI<EligiblePromotionsResponse>("/api/v1/pos/promotions/eligible", request)
      .then((resp) => {
        if (!cancelled) setData(resp);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, JSON.stringify(request)]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, error, isLoading };
}
