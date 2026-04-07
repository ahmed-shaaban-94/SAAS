"use client";

import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface LineageNode {
  name: string;
  layer: string;
  model_type: string;
}

export interface LineageEdge {
  source: string;
  target: string;
}

export interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
}

export function useLineage() {
  const { data, error, isLoading } = useSWR<LineageGraph>(
    "/api/v1/lineage/graph",
    () => fetchAPI<LineageGraph>("/api/v1/lineage/graph"),
  );

  return {
    data: data ?? { nodes: [], edges: [] },
    error,
    isLoading,
  };
}
