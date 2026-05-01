import useSWR from "swr";
import { fetchAPI, postAPI } from "@shared/lib/api-client";
import type {
  TerminalSessionResponse,
  TerminalOpenRequest,
  TerminalCloseRequest,
  ShiftSummaryResponse,
} from "@pos/types/pos";

export function usePosTerminal(siteCode?: string) {
  const key = siteCode ? `/api/v1/pos/terminals/active?site_code=${siteCode}` : null;
  const { data, error, isLoading, mutate } = useSWR<TerminalSessionResponse[]>(
    key,
    () => fetchAPI<TerminalSessionResponse[]>("/api/v1/pos/terminals/active", { site_code: siteCode }),
  );

  return {
    terminals: data ?? [],
    isLoading,
    isError: !!error,
    mutate,
  };
}

export async function openTerminal(req: TerminalOpenRequest): Promise<TerminalSessionResponse> {
  return postAPI<TerminalSessionResponse>("/api/v1/pos/terminals", req);
}

export async function pauseTerminal(terminalId: number): Promise<TerminalSessionResponse> {
  return postAPI<TerminalSessionResponse>(`/api/v1/pos/terminals/${terminalId}/pause`);
}

export async function resumeTerminal(terminalId: number): Promise<TerminalSessionResponse> {
  return postAPI<TerminalSessionResponse>(`/api/v1/pos/terminals/${terminalId}/resume`);
}

export async function closeTerminal(
  terminalId: number,
  req: TerminalCloseRequest,
): Promise<TerminalSessionResponse> {
  return postAPI<TerminalSessionResponse>(`/api/v1/pos/terminals/${terminalId}/close`, req);
}
