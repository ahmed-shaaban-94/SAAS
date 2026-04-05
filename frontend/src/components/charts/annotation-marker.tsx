"use client";

import { ReferenceLine } from "recharts";
import type { Annotation } from "@/hooks/use-annotations";

interface AnnotationMarkersProps {
  annotations: Annotation[];
  dataKey?: string;
}

/**
 * Renders Recharts ReferenceLine elements for each annotation.
 * Place these as children of any Recharts chart component.
 */
export function AnnotationMarkers({ annotations }: AnnotationMarkersProps) {
  return (
    <>
      {annotations.map((ann) => (
        <ReferenceLine
          key={ann.id}
          x={ann.data_point}
          stroke={ann.color}
          strokeDasharray="4 4"
          strokeWidth={1.5}
          label={{
            value: `\u{1F4CC} ${ann.note.slice(0, 30)}${ann.note.length > 30 ? "..." : ""}`,
            position: "top",
            fill: ann.color,
            fontSize: 10,
          }}
        />
      ))}
    </>
  );
}
