"use client";

import { useMemo } from "react";

interface Edge {
  source: string;
  target: string;
}

interface ImpactResult {
  /** Direct downstream dependents (depth 1) */
  directDependents: string[];
  /** All transitive downstream dependents (depth > 1) */
  transitiveDependents: string[];
  /** Maximum depth of downstream cascade */
  maxDepth: number;
  /** All upstream dependencies */
  upstream: string[];
  /** Map of node -> depth from selected */
  depthMap: Map<string, number>;
}

/**
 * Client-side graph traversal for lineage impact analysis.
 * Given a selected node and all edges, computes the full
 * upstream and downstream cascade.
 */
export function useLineageImpact(
  selectedNode: string | null,
  edges: Edge[],
): ImpactResult | null {
  return useMemo(() => {
    if (!selectedNode || edges.length === 0) return null;

    // Build adjacency lists
    const downstream = new Map<string, string[]>();
    const upstream = new Map<string, string[]>();

    for (const e of edges) {
      if (!downstream.has(e.source)) downstream.set(e.source, []);
      downstream.get(e.source)!.push(e.target);

      if (!upstream.has(e.target)) upstream.set(e.target, []);
      upstream.get(e.target)!.push(e.source);
    }

    // BFS downstream
    const depthMap = new Map<string, number>();
    const directDependents: string[] = [];
    const transitiveDependents: string[] = [];
    const visited = new Set<string>([selectedNode]);
    const queue: Array<{ node: string; depth: number }> = [{ node: selectedNode, depth: 0 }];
    let maxDepth = 0;

    while (queue.length > 0) {
      const { node, depth } = queue.shift()!;
      const children = downstream.get(node) ?? [];

      for (const child of children) {
        if (visited.has(child)) continue;
        visited.add(child);
        const childDepth = depth + 1;
        depthMap.set(child, childDepth);
        maxDepth = Math.max(maxDepth, childDepth);

        if (childDepth === 1) {
          directDependents.push(child);
        } else {
          transitiveDependents.push(child);
        }

        queue.push({ node: child, depth: childDepth });
      }
    }

    // BFS upstream (simpler — just collect all)
    const upstreamNodes: string[] = [];
    const visitedUp = new Set<string>([selectedNode]);
    const queueUp = [selectedNode];

    while (queueUp.length > 0) {
      const node = queueUp.shift()!;
      const parents = upstream.get(node) ?? [];

      for (const parent of parents) {
        if (visitedUp.has(parent)) continue;
        visitedUp.add(parent);
        upstreamNodes.push(parent);
        queueUp.push(parent);
      }
    }

    return {
      directDependents,
      transitiveDependents,
      maxDepth,
      upstream: upstreamNodes,
      depthMap,
    };
  }, [selectedNode, edges]);
}
