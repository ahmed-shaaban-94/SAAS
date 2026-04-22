"use client";

// bwip-js exposes toSVG at runtime but @types/bwip-js omits it.
// The cast is intentional and tested against the installed package version.
import bwipjsLib from "bwip-js";

const bwipjs = bwipjsLib as typeof bwipjsLib & {
  toSVG: (opts: Record<string, unknown>) => string;
};

interface BarcodeBlockProps {
  value: string;
}

export function BarcodeBlock({ value }: BarcodeBlockProps) {
  let svgHtml = "";
  if (value) {
    try {
      svgHtml = bwipjs.toSVG({
        bcid: "code128",
        text: value,
        scale: 2,
        height: 14,       // ~56px at 203 DPI thermal target
        includetext: false,
      });
    } catch {
      // Silently ignore render errors (e.g. invalid barcode chars)
    }
  }

  return (
    <div className="mb-3 flex flex-col items-center gap-1" dir="ltr">
      {svgHtml ? (
        <span
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: svgHtml }}
          aria-label={`Barcode for ${value}`}
          style={{ display: "block", lineHeight: 0 }}
        />
      ) : null}
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 10,
          color: "var(--pos-paper-ink-2)",
          letterSpacing: "0.04em",
        }}
      >
        {value}
      </div>
    </div>
  );
}
