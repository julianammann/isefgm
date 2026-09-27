import { describe, expect, it } from 'vitest';

import { isCrossSiteApiWrite } from './csrf.ts';

const app = new URL('http://app.test/api/v1/auth/logout');
const proxy = '/api/[...path]';

describe('isCrossSiteApiWrite', () => {
  it('lets the app itself change state through the proxy', () => {
    expect(isCrossSiteApiWrite(proxy, 'POST', 'http://app.test', app)).toBe(false);
    expect(isCrossSiteApiWrite(proxy, 'DELETE', 'http://app.test', app)).toBe(false);
  });

  it('rejects state-changing requests from another origin, whatever the Content-Type', () => {
    for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) {
      expect(isCrossSiteApiWrite(proxy, method, 'http://sibling.app.test', app)).toBe(true);
    }
    expect(isCrossSiteApiWrite(proxy, 'POST', 'https://app.test', app)).toBe(true);
    expect(isCrossSiteApiWrite(proxy, 'POST', 'null', app)).toBe(true);
  });

  it('rejects state-changing requests without an Origin header', () => {
    expect(isCrossSiteApiWrite(proxy, 'POST', null, app)).toBe(true);
  });

  it('leaves safe methods alone', () => {
    for (const method of ['GET', 'HEAD', 'OPTIONS']) {
      expect(isCrossSiteApiWrite(proxy, method, 'http://evil.example', app)).toBe(false);
      expect(isCrossSiteApiWrite(proxy, method, null, app)).toBe(false);
    }
  });

  it('only applies to /api routes; pages and form actions have their own check', () => {
    expect(isCrossSiteApiWrite('/(app)/account', 'POST', null, app)).toBe(false);
    expect(isCrossSiteApiWrite('/logout', 'POST', 'http://evil.example', app)).toBe(false);
    expect(isCrossSiteApiWrite(null, 'POST', null, app)).toBe(false);
  });
});
