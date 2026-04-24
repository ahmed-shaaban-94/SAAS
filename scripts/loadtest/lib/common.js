// Shared helpers for k6 scenarios (#607).
// No external imports — pure k6 stdlib so scenarios drop in anywhere.

import { check, fail } from 'k6';

export function baseUrl() {
  const v = __ENV.BASE_URL;
  if (!v) fail('BASE_URL env var is required');
  return v.replace(/\/$/, '');
}

export function authHeaders() {
  const token = __ENV.AUTH_TOKEN;
  if (!token) fail('AUTH_TOKEN env var is required');
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

export function tenantId() {
  return __ENV.TENANT_ID || '1';
}

// Uniform 2xx check; returns true/false so a VU can branch on it.
export function ok(res, label) {
  return check(res, {
    [`${label}: 2xx`]: (r) => r.status >= 200 && r.status < 300,
  });
}
