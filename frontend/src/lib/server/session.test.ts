import { describe, expect, it } from 'vitest';

import { parseSetCookie, safeNext } from './session.ts';

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
