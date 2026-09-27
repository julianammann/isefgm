import { describe, expect, it } from 'vitest';

import { proxyTarget, upstreamHeaders } from './proxy.ts';

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

describe('upstreamHeaders', () => {
  const incoming = new Headers({
    cookie: 'session=abc',
    'content-type': 'application/json',
    origin: 'http://app.test',
    'x-request-id': '0190c6f4-0000-7000-8000-000000000001',
    host: 'app.test',
    connection: 'keep-alive',
    'content-length': '2',
    forwarded: 'for=1.2.3.4',
    'x-forwarded-for': '1.2.3.4',
    'x-forwarded-host': 'evil.example',
    'x-forwarded-proto': 'https',
    'x-forwarded-port': '443',
    'x-real-ip': '1.2.3.4'
  });

  it('drops hop-by-hop and client-supplied forwarding headers', () => {
    const names = [...upstreamHeaders(incoming).keys()];
    expect(names.sort()).toEqual(['content-type', 'cookie', 'origin', 'x-request-id']);
  });

  it('leaves the incoming headers untouched', () => {
    upstreamHeaders(incoming);
    expect(incoming.get('x-forwarded-for')).toBe('1.2.3.4');
  });
});
