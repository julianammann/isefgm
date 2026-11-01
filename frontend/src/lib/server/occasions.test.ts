import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import type { Occasion, OccasionInput } from './occasions';
import { deleteOccasion, getOccasion, listOccasionsPage, updateOccasion } from './occasions';

const occasion: Occasion = {
  id: '01a10a3c-7d2e-7c41-9b0e-3f5a8d2c1e94',
  name: 'Hochzeitstag',
  date: '2026-06-21',
  occasion_type_id: null,
  people: [{ id: '0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71', name: 'Lena' }],
  recurrence: 'yearly',
  rule: null
};

const input: OccasionInput = {
  name: occasion.name,
  date: '2026-06-21',
  occasion_type_id: occasion.occasion_type_id,
  person_ids: occasion.people.map((person) => person.id),
  recurrence: occasion.recurrence
};

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

function createApi(handler: (request: Request) => Promise<Response>) {
  const requests: Request[] = [];
  const fetchFn: typeof fetch = (input, init) => {
    const request = input instanceof Request ? input : new Request(input, init);
    requests.push(request);
    return handler(request);
  };

  return { api: createApiClient(fetchFn, 'http://api.test'), requests };
}

describe('getOccasion', () => {
  it('fetches an occasion by its API path parameter', async () => {
    const { api, requests } = createApi(async () => jsonResponse(occasion));

    await expect(getOccasion(api, occasion.id)).resolves.toEqual({
      ok: true,
      data: occasion
    });
    expect(new URL(requests[0].url).pathname).toBe(`/api/v1/occasions/${occasion.id}`);
  });
});

describe('updateOccasion', () => {
  it('sends the full occasion data to its API path parameter', async () => {
    const { api, requests } = createApi(async () => jsonResponse(occasion));

    await expect(updateOccasion(api, occasion.id, input)).resolves.toEqual({
      ok: true,
      data: occasion
    });
    expect(requests[0].method).toBe('PUT');
    await expect(requests[0].clone().json()).resolves.toEqual(input);
  });
});

describe('deleteOccasion', () => {
  it('treats the API 204 response with no body as success', async () => {
    const { api, requests } = createApi(async () => new Response(null, { status: 204 }));

    await expect(deleteOccasion(api, occasion.id)).resolves.toEqual({
      ok: true,
      data: null
    });
    expect(requests[0].method).toBe('DELETE');
    expect(new URL(requests[0].url).pathname).toBe(`/api/v1/occasions/${occasion.id}`);
  });
});

describe('listOccasionsPage', () => {
  it('requests one page of 200 and returns items with the total', async () => {
    const { api, requests } = createApi(async () =>
      jsonResponse({ items: [occasion], offset: 0, limit: 200, total: 450 })
    );

    await expect(listOccasionsPage(api, 1)).resolves.toEqual({
      ok: true,
      data: { items: [occasion], total: 450 }
    });
    const query = new URL(requests[0].url).searchParams;
    expect(requests).toHaveLength(1);
    expect([query.get('limit'), query.get('offset')]).toEqual(['200', '0']);
  });
});
