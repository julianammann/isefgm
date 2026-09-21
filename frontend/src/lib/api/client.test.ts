import { describe, expect, it } from 'vitest';

import { createApiClient } from './client.ts';

describe('createApiClient', () => {
  it('exposes typed HTTP method', () => {
    const client = createApiClient(fetch, 'http://localhost:8000');
    expect(typeof client.GET).toBe('function');
  });
});
