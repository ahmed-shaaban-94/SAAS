/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        page: '#081826',
        card: '#102a43',
        elevated: '#163452',
        panelSoft: '#1a3550',
        surfaceStrong: '#243b53',
        border: { DEFAULT: '#33506b', divider: '#46627c' },
        ink: {
          primary: '#f7fbff',
          secondary: '#b8c0cc',
          tertiary: '#8597a8',
        },
        accent: { DEFAULT: '#00c7f2', strong: '#5cdfff' },
        chart: {
          blue: '#20bce5',
          amber: '#ffab3d',
          purple: '#7467f8',
        },
        growth: { green: '#1dd48b', red: '#ff7b7b' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card: '14px',
      },
      fontFeatureSettings: {
        tabular: '"tnum"',
      },
      backgroundImage: {
        'page-glow':
          'radial-gradient(circle at 20% 0%, rgba(0,199,242,0.08) 0%, transparent 40%), radial-gradient(circle at 80% 100%, rgba(116,103,248,0.06) 0%, transparent 45%), linear-gradient(180deg, #061320 0%, #081826 100%)',
      },
    },
  },
  plugins: [],
};
