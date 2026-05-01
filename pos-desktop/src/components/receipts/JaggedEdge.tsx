/**
 * JaggedEdge — decorative torn-paper top/bottom strip for the thermal
 * receipt preview. Inspired by the Gemini receipt mockup.
 *
 * Carries `data-torn-edge` so the print pipeline strips it
 * (see `@media print` rules in globals.css). The element renders only
 * on-screen and never affects the printed receipt.
 */

interface JaggedEdgeProps {
  /** "top" rotates the zigzag so the points face downward into the paper. */
  position: "top" | "bottom";
}

const ZIGZAG_CLIP =
  "polygon(0% 100%, 5% 0%, 10% 100%, 15% 0%, 20% 100%, 25% 0%, 30% 100%, 35% 0%, 40% 100%, 45% 0%, 50% 100%, 55% 0%, 60% 100%, 65% 0%, 70% 100%, 75% 0%, 80% 100%, 85% 0%, 90% 100%, 95% 0%, 100% 100%)";

export function JaggedEdge({ position }: JaggedEdgeProps) {
  return (
    <div
      aria-hidden="true"
      data-torn-edge=""
      data-testid={`jagged-edge-${position}`}
      style={{
        height: 10,
        width: "100%",
        background: "var(--pos-paper, #fff)",
        clipPath: ZIGZAG_CLIP,
        transform: position === "top" ? "rotate(180deg)" : undefined,
      }}
    />
  );
}
