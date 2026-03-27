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
    },
  },
  plugins: [],
};

export default config;
