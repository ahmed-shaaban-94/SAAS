// All mock data for the Dashboard. Swap with real API calls when wiring.

export const greeting = {
  name: 'Ahmed',
  dateLabel: 'Apr 18, 2026',
  syncedAgo: '2m ago',
};

export const kpis = [
  {
    id: 'revenue',
    label: 'Total Revenue',
    value: 'EGP 4.28M',
    delta: { dir: 'up', text: '12.5%' },
    sub: 'vs last month',
    color: 'accent',
    sparkline: [32, 28, 30, 22, 24, 18, 16, 20, 12, 10, 6],
  },
  {
    id: 'orders',
    label: 'Orders',
    value: '23,847',
    delta: { dir: 'up', text: '8.3%' },
    sub: '1,245 today',
    color: 'purple',
    sparkline: [24, 26, 20, 22, 18, 16, 20, 14, 16, 10, 12],
  },
  {
    id: 'stock',
    label: 'Stock Risk',
    value: '34',
    valueSuffix: 'SKUs',
    delta: { dir: 'down', text: '6 new' },
    sub: 'needing reorder',
    color: 'amber',
    sparkline: [30, 28, 26, 24, 22, 24, 20, 18, 22, 16, 14],
  },
  {
    id: 'expiry',
    label: 'Expiry Exposure',
    value: 'EGP 142K',
    delta: { dir: 'down', text: '30-day window' },
    sub: '12 batches',
    color: 'red',
    sparkline: [14, 18, 16, 22, 20, 26, 24, 30, 28, 32, 34],
  },
];

export const revenue = {
  thisMonth: 'EGP 4.28M',
  thisMonthDelta: '12.5%',
  forecast: 'EGP 4.72M',
  forecastConfidence: 92,
  target: 'EGP 4.50M',
  targetStatus: 'On track',
  // Pre-plotted path data for the prototype. Replace with real series from
  // your charting library (Recharts AreaChart, Visx, Nivo, etc).
  actualPath:
    'M0 180 C40 175 60 160 100 158 C140 156 160 170 200 160 C240 150 260 140 300 130 C340 125 360 135 400 118 C440 104 460 100 500 95',
  forecastPath: 'M500 95 C540 88 560 82 600 76 C640 70 660 68 700 60',
  todayX: 500,
  xLabels: ['Mar 20', 'Mar 28', 'Apr 5', 'Apr 24'],
};

export const channels = [
  { label: 'Retail walk-in', color: 'blue', pct: 50 },
  { label: 'Wholesale', color: 'purple', pct: 25 },
  { label: 'Institution', color: 'amber', pct: 16 },
  { label: 'Online', color: 'green', pct: 9 },
];

export const inventory = [
  { name: 'Amoxicillin 500mg · 20ct', sku: 'DP-00412', onHand: 184, daysOfStock: 3.2, velocity: 57, status: 'critical' },
  { name: 'Panadol Extra · 24ct',     sku: 'DP-00119', onHand: 312, daysOfStock: 5.8, velocity: 53, status: 'low' },
  { name: 'Insulin Lantus · 100U/ml', sku: 'DP-02041', onHand: 42,  daysOfStock: 4.1, velocity: 10, status: 'critical' },
  { name: 'Congestal · 20ct',         sku: 'DP-00873', onHand: 428, daysOfStock: 8.2, velocity: 52, status: 'low' },
  { name: 'Ventolin Inhaler · 100mcg',sku: 'DP-01556', onHand: 96,  daysOfStock: 12.4, velocity: 8, status: 'healthy' },
  { name: 'Glucophage 850mg · 30ct',  sku: 'DP-00720', onHand: 215, daysOfStock: 7.1, velocity: 30, status: 'low' },
];

// 14 weeks × 7 days = 98 cells, severity 0..5
export const expiryHeat = [
  3,1,0,2,0,4,5, 3,1,0,0,2,1,0,
  0,2,4,3,2,0,1, 0,0,1,2,3,5,4,
  2,0,1,0,3,2,0, 1,0,2,1,0,0,1,
  2,3,4,1,0,1,0, 0,1,0,2,1,0,1,
  3,1,0,0,0,1,2, 0,0,1,0,1,0,0,
  0,2,0,1,3,0,0, 1,0,0,0,0,2,1,
  0,0,0,1,0,0,0, 0,1,0,0,0,0,1,
];

export const expiryTiers = [
  { label: 'Within 30 days', value: 'EGP 48K · 4 batches', tone: 'red' },
  { label: '31-60 days',     value: 'EGP 62K · 5 batches', tone: 'amber' },
  { label: '61-90 days',     value: 'EGP 32K · 3 batches', tone: 'green' },
];

export const branches = [
  { rank: 1, name: 'Heliopolis',          region: 'Cairo',      staff: 4, revenue: 'EGP 1.12M', delta: { dir: 'up', pct: 18 } },
  { rank: 2, name: 'Nasr City',           region: 'Cairo',      staff: 3, revenue: 'EGP 920K',  delta: { dir: 'up', pct: 12 } },
  { rank: 3, name: 'Giza Downtown',       region: 'Giza',       staff: 3, revenue: 'EGP 780K',  delta: { dir: 'up', pct: 6 } },
  { rank: 4, name: 'Alexandria Corniche', region: 'Alexandria', staff: 2, revenue: 'EGP 612K',  delta: { dir: 'up', pct: 4 } },
  { rank: 5, name: 'Maadi',               region: 'Cairo',      staff: 3, revenue: 'EGP 498K',  delta: { dir: 'down', pct: 18 } },
  { rank: 6, name: '6th of October',      region: 'Giza',       staff: 2, revenue: 'EGP 358K',  delta: { dir: 'up', pct: 9 } },
];

export const anomalies = [
  {
    kind: 'down',
    title: 'Maadi branch revenue ↓ 18%',
    body: 'Unusual drop vs forecast. Correlated with stockouts in top 5 SKUs between Apr 12–17.',
    time: '2h ago',
    confidence: 'high',
  },
  {
    kind: 'up',
    title: 'Online channel spike',
    body: 'Online orders up 34% MoM driven by 3 campaigns. Consider reallocating OOH budget.',
    time: '5h ago',
    confidence: 'medium',
  },
  {
    kind: 'info',
    title: 'Data freshness: supplier feed',
    body: 'Nile Supply feed is 4 hours behind schedule. Last sync 04:12. Auto-retry in progress.',
    time: '11h ago',
    confidence: 'info',
  },
  {
    kind: 'up',
    title: 'Customer retention up',
    body: 'Repeat customer rate crossed 42% for the first time — loyalty cohort 2025-Q3.',
    time: '18h ago',
    confidence: 'high',
  },
];

export const pipeline = {
  nodes: [
    { label: 'Bronze', value: '1.13M rows', status: 'ok' },
    { label: 'Silver', value: 'Running…',   status: 'running' },
    { label: 'Gold',   value: '47 marts',   status: 'pending' },
  ],
  lastRun: { at: '04:12', duration: '8m 42s' },
  gates: '47 / 47',
  tests: '154 / 154 ✓',
  nextRun: '16:00 today',
  history: [62, 80, 45, 90, 70, 55, 72], // % heights; 70 is "warning"
  warningIndex: 4,
};

export const alert = {
  title: 'AI insight',
  body: 'Revenue in Maadi branch dropped 18% this week despite a 4% traffic increase — consistent with a stockout in top-5 SKUs. Expected impact: EGP 86K / week.',
  action: 'Investigate →',
};
