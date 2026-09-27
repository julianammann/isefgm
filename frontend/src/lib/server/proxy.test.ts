import { describe, expect, it } from 'vitest';

import { proxyTarget } from './proxy.ts';

const API = 'http://isefgm-api:8000';

describe('proxyTarget', () => {
  it('maps the rest parameter and query onto the backend /api', () => {
    expect(proxyTarget('v1/auth/me', '', API)?.href).toBe('http://isefgm-api:8000/api/v1/auth/me');
    expect(proxyTarget('v1/persons', '?page=2', API)?.href).toBe(
      'http://isefgm-api:8000/api/v1/persons?page=2'
    );
  });

  it('refuses paths that climb out of /api/', () => {
    // /api/..%2Fopenapi.json arrives decoded as '../openapi.json'.
    expect(proxyTarget('../openapi.json', '', API)).toBeNull();
    expect(proxyTarget('v1/../../docs', '', API)).toBeNull();
    expect(proxyTarget('%2e%2e/openapi.json', '', API)).toBeNull();
    expect(proxyTarget('..\\openapi.json', '', API)).toBeNull();
    expect(proxyTarget('..', '', API)).toBeNull();
  });

  it('keeps dot segments that stay inside /api/', () => {
    expect(proxyTarget('v1/x/../auth/me', '', API)?.pathname).toBe('/api/v1/auth/me');
  });

  it('never changes the backend origin', () => {
    expect(proxyTarget('/evil.example/x', '', API)?.origin).toBe(API);
    expect(proxyTarget('\\\\evil.example/x', '', API)?.origin).toBe(API);
  });
});
