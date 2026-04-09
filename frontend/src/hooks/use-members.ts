import useSWR from "swr";
import { fetchAPI, postAPI, patchAPI, deleteAPI } from "@/lib/api-client";
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

  async function updateMember(memberId: number, updates: Record<string, unknown>): Promise<void> {
    await patchAPI<MemberResponse>(`/api/v1/members/${memberId}`, updates);
    mutate();
  }

  async function removeMember(memberId: number) {
    await deleteAPI(`/api/v1/members/${memberId}`);
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
    await deleteAPI(`/api/v1/sectors/${sectorId}`);
    mutate();
  }

  return { sectors: data, isLoading, isError: !!error, mutate, createSector, deleteSector };
}
