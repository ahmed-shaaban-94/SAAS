// Dashboard first-paint scenario — 10 VUs for 60 s hitting the three
// endpoints the dashboard loads on every open.
//
// Breach thresholds → non-zero exit → CI failure (when wired).

import http from 'k6/http';
import { sleep } from 'k6';
import { authHeaders, baseUrl, ok } from '../lib/common.js';

export const options = {
  vus: 10,
  duration: '60s',
  thresholds: {
    'http_req_duration{endpoint:kpis}': ['p(95)<500'],
    'http_req_duration{endpoint:breakdown}': ['p(95)<800'],
    'http_req_duration{endpoint:trend}': ['p(95)<800'],
    'http_req_failed': ['rate<0.01'],
  },
};

export default function () {
  const url = baseUrl();
  const headers = authHeaders();

  const r1 = http.get(`${url}/api/v1/analytics/kpis`, {
    headers,
    tags: { endpoint: 'kpis' },
  });
  ok(r1, 'kpis');

  const r2 = http.get(`${url}/api/v1/analytics/breakdown?dimension=channel`, {
    headers,
    tags: { endpoint: 'breakdown' },
  });
  ok(r2, 'breakdown');

  const r3 = http.get(`${url}/api/v1/analytics/trend?metric=revenue&granularity=day`, {
    headers,
    tags: { endpoint: 'trend' },
  });
  ok(r3, 'trend');

  sleep(1);  // simulate user reading before the next refresh
}
