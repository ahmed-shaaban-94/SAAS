import type { SWRConfiguration } from "swr";

export const swrConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
  revalidateIfStale: true,
  dedupingInterval: 30000,
  focusThrottleInterval: 30000,
  errorRetryCount: 3,
  errorRetryInterval: 3000,
  keepPreviousData: true,
};
