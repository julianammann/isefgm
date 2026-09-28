/**
 * CSRF check for the browser proxy `/api/*`, applied in `hooks.server.ts` before any
 * endpoint runs.
 *
 * SvelteKit's own origin check only covers form content types, so a cross-site
 * `fetch` without a Content-Type would reach the backend with the user's cookie.
 * SameSite=Lax stops cross-site senders, but not same-site ones such as a sibling
 * subdomain.
 *
 * @module
 */

/** Methods that do not change state; everything else is checked. */
const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS'];

/**
 * `true` if a state-changing request to an `/api` route does not come from the app
 * itself. Browsers send `Origin` with every non-GET `fetch` and form submission, so a
 * missing header counts as cross-site, as in SvelteKit's check.
 *
 * `routeId` is `event.route.id`. The route decides, not `url.pathname`: SvelteKit
 * matches routes against the decoded path, so `/%61pi/...` reaches the proxy as well.
 */
export function isCrossSiteApiWrite(
  routeId: string | null,
  method: string,
  origin: string | null,
  url: URL
): boolean {
  if (!routeId?.startsWith('/api/') || SAFE_METHODS.includes(method)) return false;
  return origin !== url.origin;
}
