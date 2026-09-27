/**
 * Typed client for the backend API, generated from `openapi.json` via
 * `openapi-typescript` (see `schema.d.ts`).
 *
 * @module
 */
import createClient from 'openapi-fetch';

import type { components, paths } from './schema';

/** Client with one typed method per HTTP verb, e.g. `api.GET('/api/v1/auth/me')`. */
export type ApiClient = ReturnType<typeof createClient<paths>>;
/** Account as returned by the backend (`UserOut`). */
export type User = components['schemas']['UserOut'];
/** Error body of every non-2xx backend response. */
export type Problem = components['schemas']['Problem'];
/** Readiness of backend and database (`GET /api/v1/health/ready`). */
export type Health = components['schemas']['HealthOut'];

/**
 * Always pass the request-scoped `fetch` (from `load`, actions or hooks) and an
 * absolute `baseUrl` (on the server: `event.url.origin`). openapi-fetch constructs a
 * `Request` from `baseUrl + path`, and a relative URL throws outside the browser.
 * There is deliberately no module-level singleton for the same reason.
 */
export function createApiClient(fetchFn: typeof fetch, baseUrl: string): ApiClient {
  return createClient<paths>({ baseUrl, fetch: fetchFn });
}

/** Human-readable message from a problem-details error body, or the fallback. */
export function problemMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const p = error as Partial<Problem>;
    if (p.errors?.length) return p.errors.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join(', ');
    if (typeof p.detail === 'string' && p.detail) return p.detail;
  }
  return fallback;
}
