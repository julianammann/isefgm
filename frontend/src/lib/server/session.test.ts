import type { Cookies } from '@sveltejs/kit';
import { describe, expect, it, vi } from 'vitest';

import {
  clearSessionCookies,
  forwardSessionCookie,
  hasSessionCookie,
  parseSetCookie,
  safeNext
} from './session.ts';

/** `Cookies` stub whose request carries `jar`. */
function fakeCookies(jar: Record<string, string> = {}) {
  const stub = {
    get: vi.fn((name: string) => jar[name]),
    set: vi.fn(),
    delete: vi.fn()
  };
  return { stub, cookies: stub as unknown as Cookies };
}

/** Backend response headers carrying `setCookies`. */
function upstream(...setCookies: string[]): Headers {
  const headers = new Headers();
  for (const c of setCookies) headers.append('set-cookie', c);
  return headers;
}

describe('parseSetCookie', () => {
  it('reads name, value, Max-Age and Secure', () => {
    const c = parseSetCookie(
      'session=abc.def; HttpOnly; Max-Age=1209600; Path=/; SameSite=lax; Secure'
    );
    expect(c).toEqual({ name: 'session', value: 'abc.def', maxAge: 1209600, secure: true });
  });

  it('treats a deletion cookie as Max-Age 0', () => {
    const c = parseSetCookie(
      'session=""; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/'
    );
    expect(c?.maxAge).toBe(0);
    expect(c?.value).toBe('');
  });

  it('rejects garbage', () => {
    expect(parseSetCookie('nonsense')).toBeNull();
  });
});

describe('forwardSessionCookie', () => {
  it('copies the __Host-session cookie of a production backend', () => {
    const { stub, cookies } = fakeCookies();
    forwardSessionCookie(
      upstream('__Host-session=abc; HttpOnly; Max-Age=1209600; Path=/; SameSite=lax; Secure'),
      cookies
    );
    expect(stub.set).toHaveBeenCalledExactlyOnceWith('__Host-session', 'abc', {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: true,
      maxAge: 1209600
    });
  });

  it('copies the session cookie of a development backend without Secure', () => {
    const { stub, cookies } = fakeCookies();
    forwardSessionCookie(
      upstream('session=abc; HttpOnly; Max-Age=1209600; Path=/; SameSite=lax'),
      cookies
    );
    expect(stub.set).toHaveBeenCalledExactlyOnceWith('session', 'abc', {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: false,
      maxAge: 1209600
    });
  });

  it('deletes the cookie the backend clears, a __Host- one as Secure', () => {
    const { stub, cookies } = fakeCookies();
    forwardSessionCookie(
      upstream(
        '__Host-session=""; expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Max-Age=0; Path=/; SameSite=lax; Secure'
      ),
      cookies
    );
    expect(stub.delete).toHaveBeenCalledExactlyOnceWith('__Host-session', {
      path: '/',
      secure: true
    });
    expect(stub.set).not.toHaveBeenCalled();
  });

  it('ignores other cookies', () => {
    const { stub, cookies } = fakeCookies();
    forwardSessionCookie(
      upstream('other=abc; Path=/', '__Host-other=abc; Path=/; Secure'),
      cookies
    );
    expect(stub.set).not.toHaveBeenCalled();
    expect(stub.delete).not.toHaveBeenCalled();
  });
});

describe('hasSessionCookie', () => {
  it('recognises either name', () => {
    expect(hasSessionCookie(fakeCookies({ '__Host-session': 'abc' }).cookies)).toBe(true);
    expect(hasSessionCookie(fakeCookies({ session: 'abc' }).cookies)).toBe(true);
    expect(hasSessionCookie(fakeCookies({ other: 'abc' }).cookies)).toBe(false);
  });
});

describe('clearSessionCookies', () => {
  it('deletes whichever session cookie the browser sent, a __Host- one as Secure', () => {
    const { stub, cookies } = fakeCookies({ '__Host-session': 'a', session: 'b', other: 'c' });
    clearSessionCookies(cookies);
    expect(stub.delete.mock.calls).toEqual([
      ['__Host-session', { path: '/', secure: true }],
      ['session', { path: '/' }]
    ]);
  });

  it('leaves the response alone without a session cookie', () => {
    const { stub, cookies } = fakeCookies({ other: 'c' });
    clearSessionCookies(cookies);
    expect(stub.delete).not.toHaveBeenCalled();
  });
});

describe('safeNext', () => {
  it('allows same-origin paths only', () => {
    expect(safeNext('/persons/1')).toBe('/persons/1');
    expect(safeNext('//evil.example')).toBe('/');
    expect(safeNext('https://evil.example')).toBe('/');
    expect(safeNext(null)).toBe('/');
  });

  it('keeps query and hash', () => {
    expect(safeNext('/persons?page=2#top')).toBe('/persons?page=2#top');
  });

  it('rejects paths a browser turns into another host', () => {
    expect(safeNext('/\\evil.example')).toBe('/');
    expect(safeNext('/\t/evil.example')).toBe('/');
    expect(safeNext('/\n/evil.example')).toBe('/');
  });

  it('rejects dot segments that normalise to a protocol-relative URL', () => {
    expect(safeNext('/.//evil.example')).toBe('/');
    expect(safeNext('/%2e//evil.example')).toBe('/');
    expect(safeNext('/a/..//evil.example')).toBe('/');
    expect(safeNext('/./\\evil.example')).toBe('/');
  });

  it('falls back instead of throwing on unparsable input', () => {
    expect(safeNext('//[')).toBe('/');
  });
});
