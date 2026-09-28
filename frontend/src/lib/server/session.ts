/**
 * Session cookie handling on the SvelteKit server. Server-only: SvelteKit
 * refuses to import `$lib/server` from browser code.
 *
 * @module
 */
import type { Cookies } from '@sveltejs/kit';

/**
 * Names the backend gives the session cookie: `__Host-session` wherever it is Secure,
 * `session` in development over plain http. Must match `SESSION_COOKIE` and
 * `DEV_SESSION_COOKIE` in the backend (`core/auth.py`).
 *
 * The backend picks the name and accepts only that one, which is what keeps a cookie
 * planted by a sibling subdomain out. The frontend never picks: it recognises both,
 * forwards whichever the backend sets and deletes whichever the browser sent.
 */
export const SESSION_COOKIES: readonly string[] = ['__Host-session', 'session'];

/** Browsers drop a `__Host-` cookie without Secure or `Path=/`, deletions included. */
function isHostCookie(name: string): boolean {
  return name.startsWith('__Host-');
}

/** Deletes `name` with the attributes the browser needs to accept the deletion. */
function deleteCookie(cookies: Cookies, name: string): void {
  cookies.delete(name, isHostCookie(name) ? { path: '/', secure: true } : { path: '/' });
}

/** `true` if the browser sent a session cookie, whichever name the backend gave it. */
export function hasSessionCookie(cookies: Cookies): boolean {
  return SESSION_COOKIES.some((name) => cookies.get(name));
}

/** Deletes whichever session cookie the browser sent, e.g. after a 401 or on logout. */
export function clearSessionCookies(cookies: Cookies): void {
  for (const name of SESSION_COOKIES) {
    if (cookies.get(name)) deleteCookie(cookies, name);
  }
}

/** The parts of a backend `Set-Cookie` header that are copied to the browser. */
export interface ParsedSetCookie {
  name: string;
  value: string;
  maxAge?: number;
  secure: boolean;
}

/** Minimal Set-Cookie parser: name=value plus the attributes we forward. */
export function parseSetCookie(raw: string): ParsedSetCookie | null {
  const [pair, ...attrs] = raw.split(';').map((s) => s.trim());
  const eq = pair.indexOf('=');
  if (eq <= 0) return null;
  const parsed: ParsedSetCookie = {
    name: pair.slice(0, eq),
    value: pair.slice(eq + 1).replace(/^"|"$/g, ''),
    secure: false
  };
  for (const attr of attrs) {
    const [key, val] = attr.split('=', 2);
    const k = key.toLowerCase();
    if (k === 'max-age') parsed.maxAge = Number(val);
    if (k === 'secure') parsed.secure = true;
  }
  return parsed;
}

/**
 * The backend sets/clears the session cookie on its own response. Server-side
 * actions call the backend with event.fetch, so that cookie never reaches the
 * browser by itself: copy it onto the SvelteKit response with the same name and
 * attributes.
 */
export function forwardSessionCookie(upstream: Headers, cookies: Cookies): void {
  for (const raw of upstream.getSetCookie()) {
    const parsed = parseSetCookie(raw);
    if (!parsed || !SESSION_COOKIES.includes(parsed.name)) continue;
    if (parsed.maxAge !== undefined && parsed.maxAge <= 0) {
      deleteCookie(cookies, parsed.name);
    } else {
      cookies.set(parsed.name, parsed.value, {
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
        secure: parsed.secure || isHostCookie(parsed.name),
        maxAge: parsed.maxAge
      });
    }
  }
}

/**
 * Only same-origin paths may be used as post-login redirect targets.
 *
 * Resolved with the WHATWG URL parser, like the browser does with the `Location`
 * header: `/\evil.example` or `/<tab>/evil.example` turn into `//evil.example` there,
 * so a prefix check on the raw string is not enough. Dot segments such as
 * `/.//evil.example` keep the origin but normalise to the protocol-relative path
 * `//evil.example`, so the resolved path is checked as well.
 */
export function safeNext(next: string | null, fallback = '/'): string {
  if (!next?.startsWith('/')) return fallback;
  const base = 'http://same-origin.invalid';
  let url: URL;
  try {
    url = new URL(next, base);
  } catch {
    return fallback; // e.g. `//[`: an invalid host
  }
  if (url.origin !== base || url.pathname.startsWith('//')) return fallback;
  return url.pathname + url.search + url.hash;
}
