"use client";

import { useMemo, useState } from "react";
import { useLineage, type LineageNode } from "@/hooks/use-lineage";
import { useLineageImpact } from "@/hooks/use-lineage-impact";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { Search, AlertTriangle, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const LAYER_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  bronze: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-500" },
  silver: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-500" },
  gold: { bg: "bg-yellow-500/10", border: "border-yellow-500/30", text: "text-yellow-500" },
};

const TYPE_LABELS: Record<string, string> = {
  source: "Source",
  staging: "Staging",
  dimension: "Dimension",
  fact: "Fact",
  aggregate: "Aggregate",
  feature: "Feature",
};

interface NodeCardProps {
  node: LineageNode;
  selected: boolean;
  highlighted: boolean;
  impactDepth: number | null;
  onClick: () => void;
}

function NodeCard({ node, selected, highlighted, impactDepth, onClick }: NodeCardProps) {
  const colors = LAYER_COLORS[node.layer] ?? LAYER_COLORS.bronze;
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-lg border px-3 py-2 text-left transition-all",
        colors.bg,
        colors.border,
        selected && "ring-2 ring-accent shadow-md",
        highlighted && !selected && "ring-1 ring-red-400/50 shadow-sm",
        !highlighted && !selected && "opacity-100",
        "hover:shadow-md",
      )}
    >
      <div className="flex items-center justify-between">
        <p className={cn("text-xs font-bold", colors.text)}>{node.name}</p>
        {impactDepth !== null && impactDepth > 0 && (
          <span className="rounded-full bg-red-500/10 px-1.5 py-0.5 text-[9px] font-bold text-red-500">
            depth {impactDepth}
          </span>
        )}
      </div>
      <p className="text-[10px] text-text-tertiary">{TYPE_LABELS[node.model_type] ?? node.model_type}</p>
    </button>
  );
}

export function LineageOverview() {
  const { data, isLoading, error } = useLineage();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const impact = useLineageImpact(selectedNode, data.edges);

  const layers = useMemo(() => {
    const grouped: Record<string, LineageNode[]> = { bronze: [], silver: [], gold: [] };
    for (const node of data.nodes) {
      const layer = node.layer in grouped ? node.layer : "gold";
      grouped[layer].push(node);
    }
    for (const key of Object.keys(grouped)) {
      grouped[key].sort((a, b) => a.name.localeCompare(b.name));
    }
    return grouped;
  }, [data.nodes]);

  // Filter nodes by search
  const filteredLayers = useMemo(() => {
    if (!search.trim()) return layers;
    const q = search.toLowerCase();
    const result: Record<string, LineageNode[]> = {};
    for (const [layer, nodes] of Object.entries(layers)) {
      result[layer] = nodes.filter((n) => n.name.toLowerCase().includes(q));
    }
    return result;
  }, [layers, search]);

  // Set of all impacted nodes (upstream + downstream + selected)
  const impactedNodes = useMemo(() => {
    if (!impact || !selectedNode) return new Set<string>();
    const set = new Set<string>([selectedNode]);
    for (const n of impact.directDependents) set.add(n);
    for (const n of impact.transitiveDependents) set.add(n);
    for (const n of impact.upstream) set.add(n);
    return set;
  }, [impact, selectedNode]);

  if (isLoading) return <LoadingCard className="h-96" />;
  if (error) return <ErrorRetry title="Failed to load lineage" />;

  return (
    <div className="mt-6 space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
          <input
            type="text"
            placeholder="Search models..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="viz-panel-soft rounded-xl py-2 pl-9 pr-4 text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/30"
          />
        </div>
        <div className="flex gap-4 text-xs">
          {Object.entries(LAYER_COLORS).map(([layer, colors]) => (
            <div key={layer} className="flex items-center gap-1.5">
              <div className={`h-3 w-3 rounded ${colors.bg} ${colors.border} border`} />
              <span className="text-text-secondary capitalize">{layer}</span>
            </div>
          ))}
          <span className="text-text-tertiary ml-2">
            {data.nodes.length} models, {data.edges.length} edges
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {(["bronze", "silver", "gold"] as const).map((layer) => (
          <div key={layer} className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-text-secondary">
              {layer} ({filteredLayers[layer]?.length ?? 0})
            </h3>
            <div className="space-y-1.5">
              {(filteredLayers[layer] ?? []).map((node) => (
                <NodeCard
                  key={node.name}
                  node={node}
                  selected={selectedNode === node.name}
                  highlighted={impactedNodes.has(node.name)}
                  impactDepth={impact?.depthMap.get(node.name) ?? null}
                  onClick={() => setSelectedNode(selectedNode === node.name ? null : node.name)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {selectedNode && impact && (
        <div className="viz-panel rounded-[1.75rem] border border-accent/20 p-5 space-y-4 animate-fade-in">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-accent" />
            <h4 className="text-sm font-bold text-text-primary">
              Impact Analysis: {selectedNode}
            </h4>
          </div>

          {/* Upstream */}
          <div>
            <p className="text-xs font-medium text-text-secondary mb-1.5">
              Upstream Dependencies ({impact.upstream.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {impact.upstream.length === 0 && (
                <span className="text-xs text-text-tertiary">None (source model)</span>
              )}
              {impact.upstream.map((n) => (
                <button
                  key={n}
                  onClick={() => setSelectedNode(n)}
                  className="rounded bg-blue-500/10 px-2 py-0.5 text-xs text-blue-500 hover:bg-blue-500/20 transition-colors"
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {/* Direct dependents */}
          <div>
            <p className="text-xs font-medium text-text-secondary mb-1.5">
              Direct Dependents ({impact.directDependents.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {impact.directDependents.length === 0 && (
                <span className="text-xs text-text-tertiary">None (leaf model)</span>
              )}
              {impact.directDependents.map((n) => (
                <button
                  key={n}
                  onClick={() => setSelectedNode(n)}
                  className="rounded bg-yellow-500/10 px-2 py-0.5 text-xs text-yellow-500 hover:bg-yellow-500/20 transition-colors"
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {/* Transitive cascade */}
          {impact.transitiveDependents.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-500 mb-1.5">
                <AlertTriangle className="inline h-3 w-3 mr-1" />
                Transitive Cascade ({impact.transitiveDependents.length} models, max depth {impact.maxDepth})
              </p>
              <p className="text-[11px] text-text-secondary mb-2">
                If <strong>{selectedNode}</strong> fails, these models will also be affected:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {impact.transitiveDependents.map((n) => (
                  <button
                    key={n}
                    onClick={() => setSelectedNode(n)}
                    className="rounded bg-red-500/10 px-2 py-0.5 text-xs text-red-500 hover:bg-red-500/20 transition-colors"
                  >
                    {n}
                    <span className="ml-1 text-[9px] opacity-70">
                      (d{impact.depthMap.get(n)})
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="viz-panel-soft rounded-[1.2rem] p-3 text-xs text-text-secondary">
            <strong>Blast radius:</strong>{" "}
            {impact.directDependents.length + impact.transitiveDependents.length} downstream models affected
            {impact.maxDepth > 1 && ` across ${impact.maxDepth} layers`}
          </div>
        </div>
      )}
    </div>
  );
}
