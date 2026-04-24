// POS checkout round-trip — 5 VUs simulate 5 cashiers ringing up
// transactions at once. Hits the hot path Pharmacists care about:
//   POST /api/v1/pos/transactions/draft  (or equivalent open)
//   POST /api/v1/pos/transactions/commit
//
// p95 budget is tight — anything over 500 ms at 5 VUs is a red flag.

import http from 'k6/http';
import { sleep } from 'k6';
import { authHeaders, baseUrl, ok } from '../lib/common.js';

export const options = {
  vus: 5,
  duration: '60s',
  thresholds: {
    'http_req_duration{endpoint:commit}': ['p(95)<500', 'p(99)<800'],
    'http_req_failed': ['rate<0.01'],
  },
};

function sampleLine(i) {
  return {
    sku: `DEMO-${(i % 50) + 1}`,
    quantity: 1,
    unit_price: 12.5,
  };
}

export default function () {
  const url = baseUrl();
  const headers = authHeaders();
  const pin = __ENV.POS_PIN || '1234';

  const commit = http.post(
    `${url}/api/v1/pos/transactions/commit`,
    JSON.stringify({
      lines: [sampleLine(__ITER), sampleLine(__ITER + 1)],
      payment_method: 'cash',
      pharmacist_pin: pin,
      idempotency_key: `loadtest-${__VU}-${__ITER}-${Date.now()}`,
    }),
    { headers, tags: { endpoint: 'commit' } },
  );
  ok(commit, 'commit');

  sleep(0.5);  // cashier scans next customer — tight loop
}
