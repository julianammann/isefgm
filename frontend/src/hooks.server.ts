/**
 * Server hooks: resolve the logged-in user once per request, enforce the route guard,
 * route server-side API calls directly to the backend and set security headers.
 *
 * @module
 */
import { env } from '$env/dynamic/private';
import { error, redirect, type Handle, type HandleFetch } from '@sveltejs/kit';

import { createApiClient } from '$lib/api/client';
import { guard, SERVICE_UNAVAILABLE, type Auth } from '$lib/server/guard';
import { forwardSessionCookie, SESSION_COOKIE } from '$lib/server/session';

const API_URL = env.API_URL ?? 'http://localhost:8000';

/**
 * Server-side `fetch('/api/...')` from load functions and form actions goes straight
 * to the backend instead of through the public proxy route. The session cookie is
 * forwarded so the backend can identify the user.
 */
export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  const url = new URL(request.url);
  if (url.origin === event.url.origin && url.pathname.startsWith('/api/')) {
    request = new Request(new URL(url.pathname + url.search, API_URL), request);
    const cookie = event.request.headers.get('cookie');
    if (cookie) request.headers.set('cookie', cookie);
  }
  return fetch(request);
};

/**
 * Runs for every request: attaches a request-scoped API client and the current user
 * to `event.locals`, applies {@link guard}, then adds security headers.
 */
export const handle: Handle = async ({ event, resolve }) => {
  // One typed client per request, bound to event.fetch so handleFetch above applies.
  // The base URL must be absolute: openapi-fetch builds a `Request` before calling
  // fetch, and on the server a relative URL throws. Same origin keeps handleFetch
  // matching, which then rewrites the call to API_URL.
  event.locals.api = createApiClient(event.fetch, event.url.origin);
  event.locals.user = null;
  event.locals.authUnavailable = false;

  // Pages only: /api/* is the browser proxy, which never reads locals.user, and a
  // lookup there would double every proxied call.
  if (event.cookies.get(SESSION_COOKIE) && !event.url.pathname.startsWith('/api/')) {
    try {
      const { data, response } = await event.locals.api.GET('/api/v1/auth/me');
      if (data) {
        event.locals.user = data;
        // Sliding expiry: the backend renews the cookie on every use.
        forwardSessionCookie(response.headers, event.cookies);
      } else if (response.status === 401) {
        // Expired or revoked: drop the cookie so later requests skip the lookup.
        event.cookies.delete(SESSION_COOKIE, { path: '/' });
      } else {
        // 5xx, e.g. database down: the session may well be valid. Keep the cookie.
        event.locals.authUnavailable = true;
      }
    } catch {
      event.locals.authUnavailable = true; // backend unreachable
    }
  }

  // Before resolve(): no load function and no form action of a guarded route runs.
  // Thrown, not returned: SvelteKit then answers in the shape the client expects
  // (JSON for client-side navigation and use:enhance) and keeps cookie changes.
  const auth: Auth = event.locals.user
    ? { state: 'user', user: event.locals.user }
    : { state: event.locals.authUnavailable ? 'unknown' : 'anonymous' };
  const decision = guard(event.route.id, auth, event.url);
  if (decision.action === 'redirect') redirect(303, decision.location);
  if (decision.action === 'unavailable' && !['GET', 'HEAD'].includes(event.request.method)) {
    // Actions never run without a known user. Page views get the 503 from the
    // (app) layout load instead, which renders the regular +error.svelte.
    error(503, SERVICE_UNAVAILABLE);
  }

  const response = await resolve(event);
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-Frame-Options', 'DENY');
  return response;
};
