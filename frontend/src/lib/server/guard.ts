/**
 * Route guard, applied in `hooks.server.ts` before any load function or form action
 * runs. A guard in `+layout.server.ts` is not enough: form actions run without the
 * layout load, and page loads run in parallel with it.
 *
 * @module
 */
import type { User } from '$lib/api/client';

/** Message of the 503 page when the backend cannot tell who is logged in. */
export const SERVICE_UNAVAILABLE =
  'Der Dienst ist gerade nicht erreichbar. Bitte versuche es in ein paar Minuten erneut.';

/**
 * Who is asking, as far as the hook could tell from `/api/v1/auth/me`.
 *
 * `unknown` means the backend could not answer (unreachable or 5xx, e.g. the database
 * is down). That is not the same as logged out and must not send anyone to the login.
 */
export type Auth = { state: 'user'; user: User } | { state: 'anonymous' } | { state: 'unknown' };

/** What the hook does with the request. */
export type GuardDecision =
  { action: 'pass' } | { action: 'redirect'; location: string } | { action: 'unavailable' };

/**
 * Decides per route group:
 *
 * - `(app)` requires a login: anonymous users go to `/login?next=<path>`; if the
 *   login state is unknown, the request is answered with 503 instead, whatever the
 *   method, so no page load runs with `locals.user === null`.
 * - `(auth)` is login and registration: a logged-in user goes to `/`.
 * - Everything else passes.
 *
 * `routeId` is `event.route.id`, e.g. `/(app)/account`; `null` for unknown routes.
 */
export function guard(routeId: string | null, auth: Auth, url: URL): GuardDecision {
  if (routeId?.startsWith('/(app)')) {
    if (auth.state === 'unknown') return { action: 'unavailable' };
    if (auth.state === 'anonymous') {
      return {
        action: 'redirect',
        location: `/login?next=${encodeURIComponent(url.pathname + url.search)}`
      };
    }
  }
  if (routeId?.startsWith('/(auth)') && auth.state === 'user') {
    return { action: 'redirect', location: '/' };
  }
  return { action: 'pass' };
}
