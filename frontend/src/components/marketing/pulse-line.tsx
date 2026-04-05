"use client";

/**
 * ECG / heartbeat pulse line that animates continuously under the logo.
 * The SVG path mimics a real ECG waveform (flat → small P-wave → QRS spike → flat).
 * A clipping mask reveals the path gradually, creating the "drawing" effect.
 */
export function PulseLine() {
  return (
    <div className="relative w-full h-3 overflow-hidden" aria-hidden="true">
      <svg
        viewBox="0 0 200 20"
        preserveAspectRatio="none"
        className="w-full h-full"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Clipping rectangle that slides right to reveal the path */}
          <clipPath id="pulse-clip">
            <rect x="-200" y="0" width="200" height="20">
              <animate
                attributeName="x"
                from="-200"
                to="200"
                dur="3s"
                repeatCount="indefinite"
              />
            </rect>
          </clipPath>

          {/* Glow filter */}
          <filter id="pulse-glow">
            <feGaussianBlur stdDeviation="1" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Background flat line (dim) */}
        <line
          x1="0" y1="10" x2="200" y2="10"
          stroke="currentColor"
          strokeWidth="0.5"
          opacity="0.15"
        />

        {/* Animated ECG waveform */}
        <path
          d="M0,10 L30,10 L35,10 L38,8 L40,10 L60,10 L65,10 L68,2 L70,18 L72,6 L75,10 L95,10 L100,10 L103,8 L105,10 L130,10 L135,10 L138,8 L140,10 L160,10 L165,10 L168,2 L170,18 L172,6 L175,10 L195,10 L200,10"
          fill="none"
          stroke="var(--accent-color, #E5A00D)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          clipPath="url(#pulse-clip)"
          filter="url(#pulse-glow)"
        />
      </svg>
    </div>
  );
}
