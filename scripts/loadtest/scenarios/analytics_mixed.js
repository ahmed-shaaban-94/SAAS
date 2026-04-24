// Representative analytics read mix — ramp 0 → 20 VUs over 2 min.
// Weighted 70/20/10 across the three call classes a dashboard makes.
//
// This is the scenario that would exercise the read replica from
// PR #693 — analytics requests should not impact POS checkout
// latency when the replica URL is set.

import http from 'k6/http';
import { sleep } from 'k6';
import { authHeaders, baseUrl, ok } from '../lib/common.js';

export const options = {
  stages: [
    { duration: '30s', target: 5 },
    { duration: '60s', target: 20 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    'http_req_duration{class:kpi}': ['p(95)<500'],
    'http_req_duration{class:breakdown}': ['p(95)<1000'],
    'http_req_duration{class:trend}': ['p(95)<1000'],
    'http_req_failed': ['rate<0.02'],
  },
};

function pickClass() {
  const r = Math.random();
  if (r < 0.7) return 'kpi';
  if (r < 0.9) return 'breakdown';
  return 'trend';
}

const DIMS = ['channel', 'category', 'region', 'payment_method'];
const METRICS = ['revenue', 'units', 'margin'];

export default function () {
  const url = baseUrl();
  const headers = authHeaders();
  const c = pickClass();

  let resp;
  if (c === 'kpi') {
    resp = http.get(`${url}/api/v1/analytics/kpis`, {
      headers,
      tags: { class: c },
    });
  } else if (c === 'breakdown') {
    const dim = DIMS[Math.floor(Math.random() * DIMS.length)];
    resp = http.get(`${url}/api/v1/analytics/breakdown?dimension=${dim}`, {
      headers,
      tags: { class: c },
    });
  } else {
    const m = METRICS[Math.floor(Math.random() * METRICS.length)];
    resp = http.get(
      `${url}/api/v1/analytics/trend?metric=${m}&granularity=day`,
      { headers, tags: { class: c } },
    );
  }
  ok(resp, c);
  sleep(Math.random() * 2);
}
