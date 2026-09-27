/**
 * Pure parts of the browser proxy `routes/api/[...path]/+server.ts`.
 *
 * @module
 */

/** Headers that describe one connection and are not passed on in either direction. */
export const HOP_BY_HOP = [
  'connection',
  'content-length',
  'content-encoding',
  'host',
  'transfer-encoding'
];

/**
 * Forwarding headers as sent by the browser. They would let a client claim another IP,
 * host or scheme towards the backend, so the proxy never passes them on.
 */
const FORWARDING = [
  'forwarded',
  'x-forwarded-for',
  'x-forwarded-host',
  'x-forwarded-proto',
  'x-forwarded-port',
  'x-real-ip'
];

/** Copy of the browser's request headers without hop-by-hop and forwarding headers. */
export function upstreamHeaders(incoming: Headers): Headers {
  const headers = new Headers(incoming);
  for (const h of [...HOP_BY_HOP, ...FORWARDING]) headers.delete(h);
  return headers;
}

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
