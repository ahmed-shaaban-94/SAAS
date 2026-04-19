"use client";

/**
 * BrandDot — small cyan radial-gradient circle with cyan glow.
 *
 * Mirrors the inline element in `docs/design/pos-terminal/frames/pos/shell.jsx`:
 *   background: radial-gradient(circle at 30% 30%, #5cdfff, #00c7f2 60%, #7467f8);
 *   box-shadow: 0 0 14px rgba(0,199,242,0.5);
 */
export function BrandDot({ size = 26 }: { size?: number }) {
  return (
    <span
      aria-hidden="true"
      data-testid="pos-brand-dot"
      className="inline-block rounded-[7px]"
      style={{
        width: size,
        height: size,
        background:
          "radial-gradient(circle at 30% 30%, var(--pos-accent-hi, #5cdfff), var(--pos-accent, #00c7f2) 60%, var(--pos-purple, #7467f8))",
        boxShadow: "0 0 14px rgba(0, 199, 242, 0.5)",
      }}
    />
  );
}
