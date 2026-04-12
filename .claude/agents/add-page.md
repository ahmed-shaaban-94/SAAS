---
name: add-page
description: "Scaffold a new Next.js dashboard page with SWR hook, component, loading state, and sidebar nav. Usage: /add-page <name> <description>"
tools: [Read, Write, Edit, Glob, Grep]
---

You are adding a new page to the DataPulse Next.js dashboard. This creates 5+ files.

## Input
Parse the user's request for:
- **Page name** (e.g., `regions`, `inventory`)
- **Description** (what data it shows)
- **API endpoint** it consumes (if known)
- **Whether it has a detail page** (e.g., `/regions/[key]`)

## Steps

### 1. Create SWR Hook
Create `frontend/src/hooks/use-<name>.ts`:

```typescript
import useSWR from 'swr';
import { fetchAPI, swrKey } from '@/lib/api-client';
import { useFilters } from '@/contexts/filter-context';

export function use<Name>() {
  const { filters } = useFilters();
  return useSWR<<Name>Response>(
    swrKey('/api/v1/analytics/<endpoint>', filters),
    fetchAPI
  );
}
```

### 2. Add TypeScript Types
Edit `frontend/src/types/api.ts` — add response interface matching backend Pydantic model.

### 3. Create Main Component
Create `frontend/src/components/<name>/<name>-overview.tsx`:

```typescript
'use client';

import { use<Name> } from '@/hooks/use-<name>';
import { LoadingCard } from '@/components/loading-card';
import { ErrorRetry } from '@/components/error-retry';
import { EmptyState } from '@/components/empty-state';
import { ChartCard } from '@/components/shared/chart-card';

export function <Name>Overview() {
  const { data, error, isLoading, mutate } = use<Name>();

  if (isLoading) return <LoadingCard />;
  if (error) return <ErrorRetry onRetry={() => mutate()} />;
  if (!data) return <EmptyState message="No data available" />;

  return (
    <div className="space-y-6">
      <ChartCard title="<Title>">
        {/* Chart or table here */}
      </ChartCard>
    </div>
  );
}
```

### 4. Create Page
Create `frontend/src/app/(app)/<name>/page.tsx`:

```typescript
import { Metadata } from 'next';
import { Header } from '@/components/layout/header';
import { <Name>Overview } from '@/components/<name>/<name>-overview';

export const metadata: Metadata = {
  title: '<Title> | DataPulse',
};

export default function <Name>Page() {
  return (
    <>
      <Header title="<Title>" subtitle="<description>" />
      <main className="p-6 space-y-6">
        <Name>Overview />
      </main>
    </>
  );
}
```

### 5. Create Loading Skeleton
Create `frontend/src/app/(app)/<name>/loading.tsx`:

```typescript
import { LoadingCard } from '@/components/loading-card';

export default function Loading() {
  return (
    <div className="p-6 space-y-6">
      <LoadingCard />
      <LoadingCard />
    </div>
  );
}
```

### 6. Add to Sidebar Navigation
Edit `frontend/src/lib/constants.ts` — add nav item:
```typescript
{ name: '<Title>', href: '/<name>', icon: <IconName> },
```

### 7. Detail Page (if requested)
Create `frontend/src/app/(app)/<name>/[key]/page.tsx` with:
- `useParams()` to get key
- Dedicated detail hook `use-<name>-detail.ts`
- Back link to listing page

### 8. Verify
```bash
cd /home/user/SAAS/frontend && npx tsc --noEmit
```

### 9. Report
Show:
- All files created
- Route: `/<name>` (and `/<name>/[key]` if detail)
- Hook: `use<Name>()`
- Component: `<Name>Overview`
- Nav item added
- Remind to verify with `npm run dev`
