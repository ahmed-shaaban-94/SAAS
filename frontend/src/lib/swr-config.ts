import type { SWRConfiguration } from "swr";

const MAX_RETRY_COUNT = 3;

export const swrConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
  revalidateIfStale: true,
  dedupingInterval: 30000,
  focusThrottleInterval: 30000,
  errorRetryCount: MAX_RETRY_COUNT,
  errorRetryInterval: 3000,
  keepPreviousData: true,
  onErrorRetry(error, _key, _config, revalidate, { retryCount }) {
    // Never retry on 404 or 401 — these are permanent failures
    if (error?.status === 404 || error?.status === 401) return;
    // Stop after max retries
    if (retryCount >= MAX_RETRY_COUNT) return;
    // Exponential backoff: 1s, 2s, 4s
    const delay = Math.pow(2, retryCount) * 1000;
    setTimeout(() => revalidate({ retryCount }), delay);
  },
};
