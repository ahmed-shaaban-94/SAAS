"use client";

import { useSites } from "@/hooks/use-sites";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { MapPin } from "lucide-react";

// Simplified Egypt SVG path (outline)
const EGYPT_PATH =
  "M165,10 L200,15 L225,35 L245,25 L260,40 L275,35 L290,55 L295,75 L285,95 L295,115 L290,140 L280,155 L275,180 L260,195 L240,205 L220,200 L195,210 L170,240 L155,280 L145,320 L130,340 L110,345 L90,335 L80,310 L70,280 L60,250 L55,220 L50,195 L55,170 L65,150 L80,135 L95,115 L110,95 L120,70 L130,50 L145,30 Z";

// Real site positions based on GPS coordinates, normalized to SVG viewBox (0-100)
// Egypt bounds: lat 22.0-31.7 N, lng 24.7-36.9 E
// SVG mapping: x = (lng - 24.7) / (36.9 - 24.7) * 100, y = (31.7 - lat) / (31.7 - 22.0) * 100
function gpsToSvg(lat: number, lng: number) {
  return {
    x: ((lng - 24.7) / (36.9 - 24.7)) * 100,
    y: ((31.7 - lat) / (31.7 - 22.0)) * 100,
  };
}

// Known pharmacy site locations (from Google Maps)
const KNOWN_SITES: Record<string, { lat: number; lng: number }> = {
  // C090 — Shubra El-Kheima (شبرا الخيمة)
  "شبرا الخيمة": { lat: 30.1188, lng: 31.2662 },
  "shubra el-kheima": { lat: 30.1188, lng: 31.2662 },
  // C086 — Boulaq / Shoubra (الشرقة البولاقية)
  "الشرقة البولاقية": { lat: 30.0763, lng: 31.2485 },
  "shoubra": { lat: 30.0763, lng: 31.2485 },
};

// Fallback positions for governorates
const GOVERNORATE_POSITIONS: Record<string, { x: number; y: number }> = {
  cairo: { x: 78, y: 32 },
  alexandria: { x: 58, y: 18 },
  giza: { x: 75, y: 34 },
  luxor: { x: 72, y: 65 },
  aswan: { x: 72, y: 78 },
};

function getSitePosition(name: string, index: number) {
  // Try exact match on known sites
  const known = KNOWN_SITES[name] || KNOWN_SITES[name.toLowerCase()];
  if (known) return gpsToSvg(known.lat, known.lng);

  // Try governorate match
  const gov = GOVERNORATE_POSITIONS[name.toLowerCase()];
  if (gov) return gov;

  // Default: offset from Cairo
  return { x: 78 + index * 3, y: 32 + index * 3 };
}

export function EgyptMap() {
  const { filters } = useFilters();
  const { data, isLoading } = useSites(filters);

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
            const pos = getSitePosition(site.name, i);
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
                  stroke="#D97706"
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
                  fill="#D97706"
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
