export type RoleKey = "owner" | "admin" | "editor" | "viewer";

export interface RoleWithPermissions {
  role_id: number;
  role_key: RoleKey;
  role_name: string;
  description: string;
  is_system: boolean;
  permissions: string[];
}

export interface SectorBrief {
  sector_id: number;
  sector_key: string;
  sector_name: string;
}

export interface MemberResponse {
  member_id: number;
  tenant_id: number;
  user_id: string;
  email: string;
  display_name: string;
  role_key: RoleKey;
  role_name: string;
  is_active: boolean;
  invited_by: string | null;
  invited_at: string;
  accepted_at: string | null;
  created_at: string;
  sectors: SectorBrief[];
}

export interface SectorResponse {
  sector_id: number;
  tenant_id: number;
  sector_key: string;
  sector_name: string;
  description: string;
  site_codes: string[];
  is_active: boolean;
  created_at: string;
  member_count: number;
}

export interface AccessContextResponse {
  member_id: number;
  tenant_id: number;
  user_id: string;
  role_key: RoleKey;
  permissions: string[];
  sector_ids: number[];
  site_codes: string[];
  is_admin: boolean;
  has_full_access: boolean;
}
