"use client";

import { useEffect, useRef, useState } from "react";

export function useInView(options?: IntersectionObserverInit) {
  const ref = useRef<HTMLDivElement>(null);
  const [hasBeenVisible, setHasBeenVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || hasBeenVisible) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setHasBeenVisible(true);
        observer.disconnect();
      }
    }, { rootMargin: "200px", ...options });

    observer.observe(el);
    return () => observer.disconnect();
  }, [hasBeenVisible, options]);

  return { ref, inView: hasBeenVisible };
}
