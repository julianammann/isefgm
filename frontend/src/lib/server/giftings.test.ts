import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import {
  createGifting,
  deleteGifting,
  giftingFromForm,
  groupByGift,
  listGiftings,
  toGiftingIn,
  updateGifting,
  type GiftingOut
} from './giftings';

const given: GiftingOut = {
  id: 'g1',
  created_at: '2026-10-04T09:30:00Z',
  gift: { id: 'gift1', title: 'Raspberry Pi' },
  people: [{ id: 'p1', name: 'Lena' }],
  occasion: { id: 'o1', name: 'Weihnachten' },
  occasion_date: '2026-12-24',
  given_on: '2026-12-24',
  status: 'given'
};

describe('toGiftingIn', () => {
  it('übernimmt den vollständigen aktuellen Stand', () => {
    expect(toGiftingIn(given)).toEqual({
      gift_id: 'gift1',
      person_ids: ['p1'],
      occasion_id: 'o1',
      occasion_date: '2026-12-24',
      given_on: '2026-12-24',
      status: 'given'
    });
  });

  it('ändert nur die übergebenen Felder', () => {
    const body = toGiftingIn(given, { status: 'acquired' });
    expect(body.status).toBe('acquired');
    expect(body.person_ids).toEqual(['p1']);
    expect(body.occasion_id).toBe('o1');
  });
});

describe('giftingFromForm', () => {
  it('setzt Status idea als Standard und leere Felder auf null', () => {
    expect(giftingFromForm(new FormData(), 'gift1')).toEqual({
      gift_id: 'gift1',
      person_ids: [],
      occasion_id: null,
      occasion_date: null,
      given_on: null,
      status: 'idea'
    });
  });
});

describe('groupByGift', () => {
  it('gruppiert Beschenkungen je Idee', () => {
    const other = { ...given, id: 'g2', gift: { id: 'gift2', title: 'Buch' } };
    const grouped = groupByGift([given, other, { ...given, id: 'g3' }]);
    expect(grouped.gift1.map((g) => g.id)).toEqual(['g1', 'g3']);
    expect(grouped.gift2.map((g) => g.id)).toEqual(['g2']);
  });
});

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
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

describe('listGiftings', () => {
  it('lädt alle Seiten', async () => {
    const { api, requests } = createApi(async (request) => {
      const offset = new URL(request.url).searchParams.get('offset');
      if (offset === '0') return jsonResponse({ items: [given], offset: 0, limit: 1, total: 2 });
      return jsonResponse({ items: [{ ...given, id: 'g2' }], offset: 1, limit: 1, total: 2 });
    });

    const result = await listGiftings(api);
    expect(result.ok && result.data.map((g) => g.id)).toEqual(['g1', 'g2']);
    expect(requests).toHaveLength(2);
  });
});

describe('createGifting', () => {
  it('sendet POST mit JSON', async () => {
    const { api, requests } = createApi(async () => jsonResponse(given, 201));
    const body = toGiftingIn(given);

    await expect(createGifting(api, body)).resolves.toEqual({ ok: true, data: given });
    expect(requests[0].method).toBe('POST');
    expect(new URL(requests[0].url).pathname).toBe('/api/v1/giftings');
    await expect(requests[0].clone().json()).resolves.toEqual(body);
  });

  it('liefert 422 bei unvollständiger Beschenkung', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: [] }, 422));

    await expect(createGifting(api, { gift_id: 'gift1', status: 'given' })).resolves.toMatchObject({
      ok: false,
      status: 422
    });
  });
});

describe('updateGifting', () => {
  it('sendet PUT an die Beschenkung', async () => {
    const { api, requests } = createApi(async () => jsonResponse(given));

    await expect(updateGifting(api, 'g1', toGiftingIn(given))).resolves.toEqual({
      ok: true,
      data: given
    });
    expect(requests[0].method).toBe('PUT');
    expect(new URL(requests[0].url).pathname).toBe('/api/v1/giftings/g1');
  });
});

describe('deleteGifting', () => {
  it('liefert 404 für eine unbekannte Beschenkung', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'Not found' }, 404));

    await expect(deleteGifting(api, 'g1')).resolves.toEqual({
      ok: false,
      status: 404,
      message: 'Beschenkung nicht gefunden.'
    });
  });
});
