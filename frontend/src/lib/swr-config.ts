import type { SWRConfiguration } from "swr";

export const swrConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateIfStale: true,
  dedupingInterval: 15000,
  errorRetryCount: 3,
  errorRetryInterval: 3000,
};
