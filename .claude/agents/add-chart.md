---
name: add-chart
description: "Create a Recharts visualization component with dark/light theme support. Usage: /add-chart <type> <name> <description>"
tools: [Read, Write, Edit, Glob, Grep]
---

You are creating a new Recharts chart component for DataPulse.

## Input
Parse the user's request for:
- **Chart type**: `area`, `bar`, `line`, `pie`, `composed`, `radar`, `heatmap`
- **Component name** (e.g., `revenue-by-region-chart`)
- **Data shape** (what fields the data has)
- **Where it goes** (which page/section)

## Steps

### 1. Create Chart Component
Create `frontend/src/components/<section>/<name>.tsx`:

```typescript
'use client';

import {
  ResponsiveContainer, <ChartType>Chart, <ChartType>,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';
import { useChartTheme } from '@/hooks/use-chart-theme';
import { ChartCard } from '@/components/shared/chart-card';
import { formatCurrency, formatCompact } from '@/lib/formatters';

interface <Name>Props {
  data: Array<{
    // Define data shape
  }>;
  title?: string;
}

export function <Name>({ data, title = '<Default Title>' }: <Name>Props) {
  const theme = useChartTheme();

  if (!data?.length) return null;

  return (
    <ChartCard title={title}>
      <ResponsiveContainer width="100%" height={300}>
        <<ChartType>Chart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis
            dataKey="<xField>"
            tick={{ fill: theme.text, fontSize: 12 }}
          />
          <YAxis
            tick={{ fill: theme.text, fontSize: 12 }}
            tickFormatter={formatCompact}
          />
          <Tooltip
            formatter={(value: number) => formatCurrency(value)}
            contentStyle={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
            }}
            labelStyle={{ color: 'var(--text-primary)' }}
          />
          <<ChartType>
            dataKey="<yField>"
            stroke={theme.colors.blue}
            fill={theme.colors.blue}
            fillOpacity={0.1}
          />
        </<ChartType>Chart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
```

### Rules
- **Always use `useChartTheme()`** — never hardcode colors
- **Always use `ResponsiveContainer`** with explicit height
- **Tooltip style**: use CSS variables (`var(--bg-card)`, `var(--border-color)`)
- **Formatters**: `formatCurrency` for EGP, `formatCompact` for numbers, `formatPercent` for %
- **Font size**: 12px for axis ticks
- **Grid**: dashed (`strokeDasharray="3 3"`)

### 2. Chart Type Templates

**Area Chart** (time series): `AreaChart` + `Area` with `fillOpacity={0.1}`
**Bar Chart** (comparisons): `BarChart` + `Bar` with `radius={[4, 4, 0, 0]}`
**Horizontal Bar** (rankings): `BarChart layout="vertical"` + `Bar`
**Pie/Donut**: `PieChart` + `Pie` with `innerRadius={60}` for donut
**Composed** (bar + line): `ComposedChart` + `Bar` + `Line`
**Stacked Bar**: Multiple `Bar` components with `stackId="a"`

### 3. Integrate into Page
Import in the parent component:
```typescript
// Regular import (above fold)
import { <Name> } from '@/components/<section>/<name>';

// OR dynamic import (below fold)
const <Name> = dynamic(() => import('@/components/<section>/<name>'), {
  loading: () => <LoadingCard />,
});
```

### 4. Verify
```bash
cd /home/user/SAAS/frontend && npx tsc --noEmit
```

### 5. Report
Show:
- File created
- Chart type used
- Data shape expected
- Integration point
- Theme support confirmed
