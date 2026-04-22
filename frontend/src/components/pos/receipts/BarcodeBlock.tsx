"use client";

import bwipjs from "bwip-js";
import { useEffect, useRef } from "react";

interface BarcodeBlockProps {
  value: string;
}

export function BarcodeBlock({ value }: BarcodeBlockProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !value) return;
    try {
      bwipjs.toCanvas(canvas, {
        bcid: "code128",
        text: value,
        scale: 2,
        height: 14,       // ~56px at scale 2 (203 DPI thermal target)
        includetext: false,
        textxalign: "center",
      });
    } catch {
      // Silently ignore render errors (e.g. invalid barcode chars)
    }
  }, [value]);

  return (
    <div className="mb-3 flex flex-col items-center gap-1" dir="ltr">
      <canvas
        ref={canvasRef}
        aria-label={`Barcode for ${value}`}
        style={{ display: "block" }}
      />
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
