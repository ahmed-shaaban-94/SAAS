/**
 * Type helpers on top of the OpenAPI-generated `paths` (issue #658).
 *
 * Use these so hooks and callers can reference response/body shapes by
 * endpoint path literal without reaching into the raw `paths` tree:
 *
 *   const data = await fetchAPI<ApiGet<"/api/v1/analytics/summary">>(
 *     "/api/v1/analytics/summary",
 *   );
 *
 * The generated file (`src/generated/api.ts`) is rebuilt by
 * `npm run codegen` from `contracts/openapi.json`. Never edit it by hand.
 */
import type { paths } from "@/generated/api";

type JsonContent<T> = T extends { content: { "application/json": infer R } } ? R : never;
type Ok<R> = R extends { 200: infer T } ? T : R extends { 201: infer T } ? T : never;

/** Response body for GET `P` (2xx). */
export type ApiGet<P extends keyof paths> = paths[P] extends {
  get: { responses: infer R };
}
  ? JsonContent<Ok<R>>
  : never;

/** Response body for POST `P` (2xx). */
export type ApiPost<P extends keyof paths> = paths[P] extends {
  post: { responses: infer R };
}
  ? JsonContent<Ok<R>>
  : never;

/** Request JSON body for POST `P`. */
export type ApiPostBody<P extends keyof paths> = paths[P] extends {
  post: { requestBody?: { content: { "application/json": infer B } } };
}
  ? B
  : never;

/** Response body for PATCH `P` (2xx). */
export type ApiPatch<P extends keyof paths> = paths[P] extends {
  patch: { responses: infer R };
}
  ? JsonContent<Ok<R>>
  : never;

/** Response body for PUT `P` (2xx). */
export type ApiPut<P extends keyof paths> = paths[P] extends {
  put: { responses: infer R };
}
  ? JsonContent<Ok<R>>
  : never;
