import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        page: "#0D1117",
        card: "#161B22",
        border: "#30363D",
        divider: "#21262D",
        "text-primary": "#E6EDF3",
        "text-secondary": "#A8B3BD",
        accent: "#00BFA5",
        blue: "#2196F3",
        amber: "#FFB300",
        "growth-green": "#2E7D32",
        "growth-red": "#C62828",
      },
      fontFamily: {
        sans: ["Segoe UI", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out forwards",
        "slide-up": "slideUp 0.5s ease-out forwards",
        "glow-pulse": "glowPulse 3s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        "count-up": "countUp 2s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(0, 191, 165, 0.1)" },
          "50%": { boxShadow: "0 0 40px rgba(0, 191, 165, 0.2)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        countUp: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
