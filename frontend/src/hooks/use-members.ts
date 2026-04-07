import useSWR from "swr";
import { fetchAPI, postAPI } from "@/lib/api-client";
import type {
  AccessContextResponse,
  MemberResponse,
  RoleKey,
  RoleWithPermissions,
  SectorResponse,
} from "@/types/members";

// ── Access Context (current user) ──────────────────────────

export function useMyAccess() {
  const { data, error, isLoading, mutate } = useSWR<AccessContextResponse>(
    "/api/v1/members/me",
    () => fetchAPI<AccessContextResponse>("/api/v1/members/me"),
  );
  return { access: data, isLoading, isError: !!error, mutate };
}

// ── Roles ──────────────────────────────────────────────────

export function useRoles() {
  const { data, error, isLoading } = useSWR<RoleWithPermissions[]>(
    "/api/v1/members/roles",
    () => fetchAPI<RoleWithPermissions[]>("/api/v1/members/roles"),
  );
  return { roles: data, isLoading, isError: !!error };
}

// ── Members ────────────────────────────────────────────────

export function useMembers() {
  const { data, error, isLoading, mutate } = useSWR<MemberResponse[]>(
    "/api/v1/members",
    () => fetchAPI<MemberResponse[]>("/api/v1/members"),
  );

  async function inviteMember(email: string, role_key: RoleKey, display_name: string, sector_ids: number[]) {
    const res = await postAPI<MemberResponse>("/api/v1/members", {
      email,
      role_key,
      display_name,
      sector_ids,
    });
    mutate();
    return res;
  }

  async function updateMember(memberId: number, updates: Record<string, unknown>) {
    const url = `/api/v1/members/${memberId}`;
    const res = await fetchAPI<MemberResponse>(url, undefined);
    // Use PATCH
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}${url}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error(`Failed to update member: ${response.status}`);
    mutate();
    return response.json();
  }

  async function removeMember(memberId: number) {
    const url = `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/members/${memberId}`;
    const response = await fetch(url, { method: "DELETE" });
    if (!response.ok) throw new Error(`Failed to remove member: ${response.status}`);
    mutate();
  }

  return { members: data, isLoading, isError: !!error, mutate, inviteMember, updateMember, removeMember };
}

// ── Sectors ────────────────────────────────────────────────

export function useSectors() {
  const { data, error, isLoading, mutate } = useSWR<SectorResponse[]>(
    "/api/v1/sectors",
    () => fetchAPI<SectorResponse[]>("/api/v1/sectors"),
  );

  async function createSector(sector: { sector_key: string; sector_name: string; description?: string; site_codes?: string[] }) {
    const res = await postAPI<SectorResponse>("/api/v1/sectors", sector);
    mutate();
    return res;
  }

  async function deleteSector(sectorId: number) {
    const url = `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/sectors/${sectorId}`;
    const response = await fetch(url, { method: "DELETE" });
    if (!response.ok) throw new Error(`Failed to delete sector: ${response.status}`);
    mutate();
  }

  return { sectors: data, isLoading, isError: !!error, mutate, createSector, deleteSector };
}
