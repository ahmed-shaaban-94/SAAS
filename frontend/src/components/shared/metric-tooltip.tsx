"use client";

import { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { Info } from "lucide-react";

interface MetricTooltipProps {
  description: string;
}

export function MetricTooltip({ description }: MetricTooltipProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          className="inline-flex items-center justify-center rounded-full p-0.5 text-text-secondary/50 transition-colors hover:text-text-secondary focus:outline-none"
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
          aria-label="Metric info"
        >
          <Info className="h-3.5 w-3.5" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-50 max-w-xs rounded-lg border border-border bg-card/95 px-3 py-2 text-xs text-text-secondary shadow-xl backdrop-blur-sm"
          sideOffset={5}
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
        >
          {description}
          <Popover.Arrow className="fill-border" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
