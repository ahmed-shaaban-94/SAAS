"use client";

import { useMemo, useState } from "react";
import { useLineage, LineageNode } from "@/hooks/use-lineage";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";

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

function NodeCard({ node, selected, onClick }: { node: LineageNode; selected: boolean; onClick: () => void }) {
  const colors = LAYER_COLORS[node.layer] ?? LAYER_COLORS.bronze;
  return (
    <button
      onClick={onClick}
      className={`rounded-lg border px-3 py-2 text-left transition-all ${colors.bg} ${selected ? "ring-2 ring-accent" : ""} ${colors.border} hover:shadow-md`}
    >
      <p className={`text-xs font-bold ${colors.text}`}>{node.name}</p>
      <p className="text-[10px] text-text-tertiary">{TYPE_LABELS[node.model_type] ?? node.model_type}</p>
    </button>
  );
}

export function LineageOverview() {
  const { data, isLoading, error } = useLineage();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const layers = useMemo(() => {
    const grouped: Record<string, LineageNode[]> = { bronze: [], silver: [], gold: [] };
    for (const node of data.nodes) {
      const layer = node.layer in grouped ? node.layer : "gold";
      grouped[layer].push(node);
    }
    // Sort nodes alphabetically within each layer
    for (const key of Object.keys(grouped)) {
      grouped[key].sort((a, b) => a.name.localeCompare(b.name));
    }
    return grouped;
  }, [data.nodes]);

  const connectedNodes = useMemo(() => {
    if (!selectedNode) return new Set<string>();
    const connected = new Set<string>([selectedNode]);
    for (const e of data.edges) {
      if (e.source === selectedNode) connected.add(e.target);
      if (e.target === selectedNode) connected.add(e.source);
    }
    return connected;
  }, [selectedNode, data.edges]);

  if (isLoading) return <LoadingCard className="h-96" />;
  if (error) return <ErrorRetry title="Failed to load lineage" />;

  return (
    <div className="space-y-6 mt-6">
      {/* Legend */}
      <div className="flex gap-4 text-xs">
        {Object.entries(LAYER_COLORS).map(([layer, colors]) => (
          <div key={layer} className="flex items-center gap-1.5">
            <div className={`h-3 w-3 rounded ${colors.bg} ${colors.border} border`} />
            <span className="text-text-secondary capitalize">{layer}</span>
          </div>
        ))}
        <span className="text-text-tertiary ml-4">
          {data.nodes.length} models, {data.edges.length} edges
        </span>
      </div>

      {/* Layer columns */}
      <div className="grid grid-cols-3 gap-6">
        {(["bronze", "silver", "gold"] as const).map((layer) => (
          <div key={layer} className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-text-secondary">
              {layer} ({layers[layer]?.length ?? 0})
            </h3>
            <div className="space-y-1.5">
              {(layers[layer] ?? []).map((node) => (
                <NodeCard
                  key={node.name}
                  node={node}
                  selected={selectedNode === node.name}
                  onClick={() => setSelectedNode(selectedNode === node.name ? null : node.name)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Selected node details */}
      {selectedNode && (
        <div className="rounded-xl border border-accent/30 bg-accent/5 p-4">
          <h4 className="text-sm font-bold text-text-primary mb-2">{selectedNode}</h4>
          <div className="grid gap-2 md:grid-cols-2 text-xs">
            <div>
              <p className="font-medium text-text-secondary mb-1">Upstream (depends on):</p>
              <div className="flex flex-wrap gap-1">
                {data.edges.filter((e) => e.target === selectedNode).map((e) => (
                  <span key={e.source} className="rounded bg-blue-500/10 px-2 py-0.5 text-blue-500">
                    {e.source}
                  </span>
                ))}
                {data.edges.filter((e) => e.target === selectedNode).length === 0 && (
                  <span className="text-text-tertiary">None (source)</span>
                )}
              </div>
            </div>
            <div>
              <p className="font-medium text-text-secondary mb-1">Downstream (used by):</p>
              <div className="flex flex-wrap gap-1">
                {data.edges.filter((e) => e.source === selectedNode).map((e) => (
                  <span key={e.target} className="rounded bg-yellow-500/10 px-2 py-0.5 text-yellow-500">
                    {e.target}
                  </span>
                ))}
                {data.edges.filter((e) => e.source === selectedNode).length === 0 && (
                  <span className="text-text-tertiary">None (leaf)</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
