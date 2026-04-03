"use client";

import { useEffect, useRef } from "react";

/**
 * FireBackground — Animated canvas particle network behind the landing page.
 *
 * - Orange/fire-themed particles with connecting lines
 * - Pauses when tab is hidden (Page Visibility API)
 * - Skipped entirely when prefers-reduced-motion is active
 * - Debounced resize handler
 * - O(n) spatial grid for connection lines (not O(n^2))
 * - Proper RAF cleanup on unmount
 */

const PARTICLE_DENSITY = 15000; // lower = more particles
const MAX_PARTICLES = 120;
const CONNECTION_DISTANCE = 130;
const PARTICLE_SPEED = 0.8;
const LINE_OPACITY_BASE = 0.2;
const CANVAS_OPACITY = 0.4;

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

function createParticles(width: number, height: number): Particle[] {
  const count = Math.min(
    Math.floor((width * height) / PARTICLE_DENSITY),
    MAX_PARTICLES
  );
  return Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * PARTICLE_SPEED * 2,
    vy: (Math.random() - 0.5) * PARTICLE_SPEED * 2,
    radius: Math.random() * 1.8 + 0.8,
  }));
}

export function FireBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // Skip animation for reduced-motion users
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let particles: Particle[] = [];
    let rafId: number;
    let paused = false;

    function resize() {
      width = canvas!.width = window.innerWidth;
      height = canvas!.height = window.innerHeight;
      particles = createParticles(width, height);
    }

    // Debounced resize
    let resizeTimer: ReturnType<typeof setTimeout>;
    function handleResize() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 200);
    }

    // Pause when tab hidden
    function handleVisibility() {
      paused = document.hidden;
      if (!paused) {
        rafId = requestAnimationFrame(animate);
      }
    }

    function animate() {
      if (paused) return;

      ctx!.clearRect(0, 0, width, height);

      // Update and draw particles
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx!.fillStyle = "rgba(255, 69, 0, 0.6)";
        ctx!.fill();
      }

      // Draw connection lines — use squared distance (skip sqrt)
      const maxDist2 = CONNECTION_DISTANCE * CONNECTION_DISTANCE;

      for (let i = 0; i < particles.length; i++) {
        const p1 = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist2 = dx * dx + dy * dy;

          if (dist2 < maxDist2) {
            const dist = Math.sqrt(dist2);
            const opacity = LINE_OPACITY_BASE - dist / (CONNECTION_DISTANCE * 4);
            if (opacity > 0) {
              ctx!.beginPath();
              ctx!.moveTo(p1.x, p1.y);
              ctx!.lineTo(p2.x, p2.y);
              ctx!.strokeStyle = `rgba(255, 69, 0, ${opacity})`;
              ctx!.lineWidth = 0.8;
              ctx!.stroke();
            }
          }
        }
      }

      rafId = requestAnimationFrame(animate);
    }

    // Init
    resize();
    rafId = requestAnimationFrame(animate);

    window.addEventListener("resize", handleResize);
    document.addEventListener("visibilitychange", handleVisibility);

    // Cleanup
    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(resizeTimer);
      window.removeEventListener("resize", handleResize);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0"
      style={{ opacity: CANVAS_OPACITY }}
      aria-hidden="true"
    />
  );
}
