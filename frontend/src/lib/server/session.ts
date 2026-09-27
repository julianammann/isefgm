/**
 * Session cookie handling on the SvelteKit server. Server-only: SvelteKit
 * refuses to import `$lib/server` from browser code.
 *
 * @module
 */
import type { Cookies } from '@sveltejs/kit';

/** Name of the session cookie; must match `SESSION_COOKIE` in the backend. */
export const SESSION_COOKIE = 'session';

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
 * browser by itself: copy it onto the SvelteKit response with the same attributes.
 */
export function forwardSessionCookie(upstream: Headers, cookies: Cookies): void {
  for (const raw of upstream.getSetCookie()) {
    const parsed = parseSetCookie(raw);
    if (parsed?.name !== SESSION_COOKIE) continue;
    if (parsed.maxAge !== undefined && parsed.maxAge <= 0) {
      cookies.delete(SESSION_COOKIE, { path: '/' });
    } else {
      cookies.set(SESSION_COOKIE, parsed.value, {
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
        secure: parsed.secure,
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
