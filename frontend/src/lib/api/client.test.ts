import { describe, expect, it } from 'vitest';

import { createApiClient } from './client.ts';

describe('createApiClient', () => {
  it('exposes typed HTTP method', () => {
    const client = createApiClient(fetch, 'http://localhost:8000');
    expect(typeof client.GET).toBe('function');
  });

  // Runs in Node like hooks.server.ts: openapi-fetch builds a Request before fetch,
  // which fails for a relative URL. The client must send an absolute one.
  it('requests an absolute URL on the server', async () => {
    const seen: string[] = [];
    const fakeFetch = async (input: RequestInfo | URL) => {
      seen.push(input instanceof Request ? input.url : String(input));
      return new Response('{}', { headers: { 'content-type': 'application/json' } });
    };
    const client = createApiClient(fakeFetch as typeof fetch, 'http://app.test');
    await client.GET('/api/v1/auth/me');
    expect(seen).toEqual(['http://app.test/api/v1/auth/me']);
  });
});
