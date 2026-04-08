"use client";

import { Activity } from "lucide-react";
import { useBrandContext } from "./brand-provider";

interface BrandLogoProps {
  className?: string;
  showText?: boolean;
}

export function BrandLogo({ className, showText = true }: BrandLogoProps) {
  const branding = useBrandContext();

  if (branding?.logo_url) {
    return (
      <div className={className}>
        <img
          src={branding.logo_url}
          alt={branding.company_name}
          className="h-6 w-auto object-contain"
        />
        {showText && (
          <span className="text-xl font-bold text-accent">
            {branding.company_name}
          </span>
        )}
      </div>
    );
  }

  const name = branding?.company_name || "DataPulse";
  const hideBranding = branding?.hide_datapulse_branding;

  return (
    <div className={className}>
      {!hideBranding && <Activity className="h-6 w-6 text-accent" />}
      {showText && (
        <span className="text-xl font-bold text-accent">{name}</span>
      )}
    </div>
  );
}
