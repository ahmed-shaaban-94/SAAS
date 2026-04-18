"use client";

/**
 * Trigger wrapper — makes any metric display clickable and wires it to
 * a Why-Changed modal. Provides a dashed-underline affordance so users
 * learn that any number in the dashboard can be decomposed.
 *
 * Usage:
 *   <WhyChangedTrigger data={mtdRevenueWhy}>
 *     <span className="value">EGP 4.72M</span>
 *   </WhyChangedTrigger>
 */

import { useState } from "react";
import { WhyChanged, type WhyChangedData } from "./why-changed";

interface Props {
  data: WhyChangedData;
  children: React.ReactNode;
  /** Render the wrapper as inline-span rather than a block button. */
  inline?: boolean;
  "aria-label"?: string;
}

export function WhyChangedTrigger({ data, children, inline, ...rest }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="wc-trigger"
        onClick={() => setOpen(true)}
        aria-label={rest["aria-label"] ?? `Why did ${data.totalLabel} change?`}
        style={inline ? { display: "inline" } : undefined}
      >
        {children}
      </button>
      <WhyChanged open={open} onClose={() => setOpen(false)} data={data} />
    </>
  );
}
