"use client";

import { useEffect, useState } from "react";

interface TypingSubtitleProps {
  text: string;
  speed?: number;
  className?: string;
}

export function TypingSubtitle({ text, speed = 28, className = "" }: TypingSubtitleProps) {
  const [displayed, setDisplayed] = useState("");
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion) {
      setDisplayed(text);
      setShowCursor(false);
      return;
    }

    let i = 0;
    const timer = setInterval(() => {
      if (i <= text.length) {
        setDisplayed(text.substring(0, i));
        i++;
      } else {
        clearInterval(timer);
        setTimeout(() => setShowCursor(false), 2000);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed]);

  return (
    <span className={`${className} ${showCursor ? "typing-cursor" : ""}`}>
      {displayed}
    </span>
  );
}
