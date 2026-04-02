"use client";

import { useSites } from "@/hooks/use-sites";
import { formatCurrency } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { MapPin } from "lucide-react";

// Simplified Egypt SVG path (outline)
const EGYPT_PATH =
  "M165,10 L200,15 L225,35 L245,25 L260,40 L275,35 L290,55 L295,75 L285,95 L295,115 L290,140 L280,155 L275,180 L260,195 L240,205 L220,200 L195,210 L170,240 L155,280 L145,320 L130,340 L110,345 L90,335 L80,310 L70,280 L60,250 L55,220 L50,195 L55,170 L65,150 L80,135 L95,115 L110,95 L120,70 L130,50 L145,30 Z";

// Approximate positions for Egyptian governorates (normalized 0-100 within the SVG viewBox)
const SITE_POSITIONS: Record<string, { x: number; y: number }> = {
  cairo: { x: 78, y: 32 },
  alexandria: { x: 58, y: 18 },
  giza: { x: 75, y: 34 },
  luxor: { x: 72, y: 65 },
  aswan: { x: 72, y: 78 },
  default_1: { x: 78, y: 32 },
  default_2: { x: 58, y: 18 },
};

export function EgyptMap() {
  const { data, isLoading } = useSites();

  if (isLoading) return <LoadingCard className="h-72" />;

  const sites = data?.items ?? [];

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <MapPin className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">
          Site Locations
        </h3>
      </div>

      <div className="relative">
        <svg viewBox="0 0 320 360" className="mx-auto h-56 w-full">
          {/* Egypt outline */}
          <path
            d={EGYPT_PATH}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-border"
            opacity="0.6"
          />
          <path d={EGYPT_PATH} fill="currentColor" className="text-accent/5" />

          {/* Site markers */}
          {sites.map((site, i) => {
            const pos =
              SITE_POSITIONS[site.name.toLowerCase()] ||
              SITE_POSITIONS[`default_${i + 1}`] ||
              { x: 50 + i * 20, y: 30 + i * 10 };
            const x = pos.x * 3.2;
            const y = pos.y * 3.6;

            return (
              <g key={site.key}>
                {/* Pulse ring */}
                <circle
                  cx={x}
                  cy={y}
                  r="12"
                  fill="none"
                  stroke="#00BFA5"
                  strokeWidth="1"
                  opacity="0.3"
                >
                  <animate
                    attributeName="r"
                    values="8;16;8"
                    dur="3s"
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    values="0.5;0;0.5"
                    dur="3s"
                    repeatCount="indefinite"
                  />
                </circle>
                {/* Pin */}
                <circle
                  cx={x}
                  cy={y}
                  r="6"
                  fill="#00BFA5"
                  stroke="white"
                  strokeWidth="2"
                />
                {/* Label */}
                <text
                  x={x + 10}
                  y={y - 8}
                  className="fill-text-primary text-[10px] font-medium"
                >
                  {site.name}
                </text>
                <text
                  x={x + 10}
                  y={y + 4}
                  className="fill-text-secondary text-[9px]"
                >
                  {formatCurrency(site.value)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Site list below map */}
      <div className="mt-2 space-y-1">
        {sites.map((site) => (
          <div
            key={site.key}
            className="flex items-center justify-between rounded px-2 py-1 text-xs hover:bg-divider"
          >
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-accent" />
              <span className="font-medium text-text-primary">{site.name}</span>
            </div>
            <span className="text-text-secondary">
              {formatCurrency(site.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
