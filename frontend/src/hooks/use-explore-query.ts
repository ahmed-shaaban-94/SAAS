import { useState, useCallback } from "react";
import { postAPI } from "@/lib/api-client";
import type { ExploreQueryRequest, ExploreResult } from "@/types/api";

export function useExploreQuery() {
  const [data, setData] = useState<ExploreResult | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const execute = useCallback(async (query: ExploreQueryRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await postAPI<ExploreResult>(
        "/api/v1/explore/query",
        query,
      );
      setData(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, error, isLoading, execute, reset };
}
