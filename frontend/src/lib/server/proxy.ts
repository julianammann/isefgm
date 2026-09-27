/**
 * Pure parts of the browser proxy `routes/api/[...path]/+server.ts`.
 *
 * @module
 */

/**
 * Backend URL for a proxied request, or `null` if it would leave `/api/` on the backend.
 *
 * `path` is the decoded rest parameter: `/api/..%2Fopenapi.json` arrives as
 * `../openapi.json`, which the URL parser resolves to `/openapi.json`. The resolved
 * URL is therefore checked, not the input.
 */
export function proxyTarget(path: string, search: string, apiUrl: string): URL | null {
  const base = new URL(apiUrl);
  const target = new URL(`/api/${path}${search}`, base);
  if (target.origin !== base.origin || !target.pathname.startsWith('/api/')) return null;
  return target;
}
