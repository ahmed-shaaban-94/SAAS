"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";

// ── Types ───────────────────────────────────────────────────────────

export interface BadgeResponse {
  badge_id: number;
  badge_key: string;
  title_en: string;
  title_ar?: string | null;
  description_en: string;
  description_ar?: string | null;
  icon: string;
  tier: string;
  category: string;
  is_active: boolean;
}

export interface StaffBadgeResponse {
  badge_id: number;
  badge_key: string;
  title_en: string;
  title_ar?: string | null;
  icon: string;
  tier: string;
  category: string;
  earned_at: string;
  context: Record<string, unknown>;
}

export interface StreakResponse {
  streak_type: string;
  current_count: number;
  best_count: number;
  last_date: string | null;
}

export interface StaffLevelResponse {
  staff_key: number;
  level: number;
  total_xp: number;
  current_tier: string;
  xp_to_next_level: number;
}

export interface GamificationProfile {
  staff_key: number;
  staff_name: string;
  level: number;
  total_xp: number;
  current_tier: string;
  xp_to_next_level: number;
  badges: StaffBadgeResponse[];
  streaks: StreakResponse[];
  badge_count: number;
}

export interface LeaderboardEntry {
  rank: number;
  staff_key: number;
  staff_name: string;
  level: number;
  total_xp: number;
  current_tier: string;
  badge_count: number;
}

export interface CompetitionResponse {
  competition_id: number;
  title: string;
  description: string;
  competition_type: string;
  metric: string;
  start_date: string;
  end_date: string;
  status: string;
  prize_description: string | null;
  created_at: string;
}

export interface CompetitionEntryResponse {
  staff_key: number;
  staff_name: string;
  score: number;
  rank: number | null;
}

export interface CompetitionDetail {
  competition: CompetitionResponse;
  entries: CompetitionEntryResponse[];
}

export interface FeedItem {
  id: number;
  staff_key: number;
  staff_name: string;
  event_type: string;
  title: string;
  description: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface XPEvent {
  id: number;
  xp_amount: number;
  source: string;
  source_ref: string | null;
  earned_at: string;
}

// ── Hooks ───────────────────────────────────────────────────────────

export function useGamificationProfile(staffKey: number) {
  const { data, error, isLoading, mutate } = useSWR<GamificationProfile>(
    staffKey ? `/api/v1/gamification/profile/${staffKey}` : null,
    () => fetchAPI<GamificationProfile>(`/api/v1/gamification/profile/${staffKey}`),
  );
  return { data, error, isLoading, mutate };
}

export function useBadges() {
  const { data, error, isLoading } = useSWR<BadgeResponse[]>(
    "/api/v1/gamification/badges",
    () => fetchAPI<BadgeResponse[]>("/api/v1/gamification/badges"),
  );
  return { data, error, isLoading };
}

export function useStaffBadges(staffKey: number) {
  const { data, error, isLoading } = useSWR<StaffBadgeResponse[]>(
    staffKey ? `/api/v1/gamification/badges/${staffKey}` : null,
    () => fetchAPI<StaffBadgeResponse[]>(`/api/v1/gamification/badges/${staffKey}`),
  );
  return { data, error, isLoading };
}

export function useStreaks(staffKey: number) {
  const { data, error, isLoading } = useSWR<StreakResponse[]>(
    staffKey ? `/api/v1/gamification/streaks/${staffKey}` : null,
    () => fetchAPI<StreakResponse[]>(`/api/v1/gamification/streaks/${staffKey}`),
  );
  return { data, error, isLoading };
}

export function useXPLeaderboard(limit: number = 20) {
  const { data, error, isLoading } = useSWR<LeaderboardEntry[]>(
    ["/api/v1/gamification/leaderboard", limit],
    () => fetchAPI<LeaderboardEntry[]>("/api/v1/gamification/leaderboard", { limit }),
  );
  return { data, error, isLoading };
}

export function useCompetitions(status?: string) {
  const { data, error, isLoading, mutate } = useSWR<CompetitionResponse[]>(
    ["/api/v1/gamification/competitions", status],
    () => fetchAPI<CompetitionResponse[]>("/api/v1/gamification/competitions", status ? { status } : undefined),
  );
  return { data, error, isLoading, mutate };
}

export function useCompetitionDetail(competitionId: number) {
  const { data, error, isLoading } = useSWR<CompetitionDetail>(
    competitionId ? `/api/v1/gamification/competitions/${competitionId}` : null,
    () => fetchAPI<CompetitionDetail>(`/api/v1/gamification/competitions/${competitionId}`),
  );
  return { data, error, isLoading };
}

export function useActivityFeed(limit: number = 30) {
  const { data, error, isLoading } = useSWR<FeedItem[]>(
    ["/api/v1/gamification/feed", limit],
    () => fetchAPI<FeedItem[]>("/api/v1/gamification/feed", { limit }),
    { refreshInterval: 30_000 },
  );
  return { data, error, isLoading };
}

export function useXPHistory(staffKey: number, limit: number = 50) {
  const { data, error, isLoading } = useSWR<XPEvent[]>(
    staffKey ? [`/api/v1/gamification/xp/${staffKey}/history`, limit] : null,
    () => fetchAPI<XPEvent[]>(`/api/v1/gamification/xp/${staffKey}/history`, { limit }),
  );
  return { data, error, isLoading };
}
