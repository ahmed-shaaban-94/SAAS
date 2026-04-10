"use client";

import { useEffect, useState } from "react";

export function MouseGlow() {
  const [pos, setPos] = useState({ x: -1000, y: -1000 }); // start off-screen

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      setPos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden motion-reduce:hidden"
    >
      <div
        className="absolute rounded-full"
        style={{
          width: 600,
          height: 600,
          left: pos.x - 300,
          top: pos.y - 300,
          // --accent-color is #E5A00D (amber) in the marketing dark layout
          background:
            "radial-gradient(circle, rgba(229, 160, 13, 0.25) 0%, rgba(229, 160, 13, 0.05) 50%, transparent 70%)",
          opacity: 0.2,
          pointerEvents: "none",
          transition: "left 0.15s ease-out, top 0.15s ease-out",
          willChange: "left, top",
        }}
      />
    </div>
  );
}
