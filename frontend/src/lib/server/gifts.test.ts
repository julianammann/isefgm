import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import type { GiftOut } from './gifts';
import { createGift, deleteGift, giftFromForm, isPrice, listGifts, updateGift } from './gifts';

const gift: GiftOut = {
  id: '0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70',
  title: 'Raspberry Pi',
  category: 'tech',
  created_at: '2026-10-18T12:00:00Z',
  description: null,
  price_from: null,
  price_to: null,
  currency: null,
  people: [],
  occasions: []
};

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

describe('giftFromForm', () => {
  it('needs only the title and sets the defaults', () => {
    const f = new FormData();
    f.set('title', '  Raspberry Pi ');
    expect(giftFromForm(f)).toEqual({
      title: 'Raspberry Pi',
      description: null,
      category: 'other',
      price_from: null,
      price_to: null,
      currency: null,
      person_ids: [],
      occasion_ids: []
    });
  });

  it('turns a decimal comma into a point', () => {
    const f = new FormData();
    f.set('title', 'Buch');
    f.set('price_from', '10,50');
    expect(giftFromForm(f).price_from).toBe('10.50');
  });

  it('normalises the currency code to capital letters', () => {
    const f = new FormData();
    f.set('title', 'Buch');
    f.set('price_from', '10');
    f.set('currency', 'eur');
    expect(giftFromForm(f).currency).toBe('EUR');
  });
});

describe('isPrice', () => {
  it('accepts whole prices and up to two decimal places', () => {
    for (const price of ['0', '10', '10.5', '10.99', '12345678.99']) {
      expect(isPrice(price), price).toBe(true);
    }
  });

  it('rejects what the backend would reject with 422', () => {
    for (const price of [
      '10.999',
      '123456789',
      '-1',
      '1e3',
      '0x10',
      '1.000.50',
      '10.',
      '.5',
      'abc'
    ]) {
      expect(isPrice(price), price).toBe(false);
    }
  });
});

describe('listGifts', () => {
  it('loads every page using the number of collected ideas as the next offset', async () => {
    const second = { ...gift, id: '0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71', title: 'Buch' };
    const { api, requests } = createApi(async (request) => {
      const offset = new URL(request.url).searchParams.get('offset');
      if (offset === '0') return jsonResponse({ items: [gift], offset: 0, limit: 1, total: 2 });
      return jsonResponse({ items: [second], offset: 1, limit: 1, total: 2 });
    });

    await expect(listGifts(api)).resolves.toEqual({ ok: true, data: [gift, second] });
    expect(requests.map((request) => new URL(request.url).searchParams.get('offset'))).toEqual([
      '0',
      '1'
    ]);
  });

  it('returns the backend error for a failed page request', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'Unauthorized' }, 401));

    await expect(listGifts(api)).resolves.toEqual({
      ok: false,
      status: 401,
      message: 'Sitzung abgelaufen. Bitte erneut anmelden.'
    });
  });
});

describe('createGift', () => {
  it('sends POST with JSON and returns the created idea', async () => {
    const { api, requests } = createApi(async () => jsonResponse(gift, 201));

    await expect(createGift(api, { title: 'Raspberry Pi', category: 'tech' })).resolves.toEqual({
      ok: true,
      data: gift
    });
    expect(requests[0].method).toBe('POST');
    expect(new URL(requests[0].url).pathname).toBe('/api/v1/gifts');
    await expect(requests[0].clone().json()).resolves.toEqual({
      title: 'Raspberry Pi',
      category: 'tech'
    });
  });

  it('maps a network failure to 502', async () => {
    const { api } = createApi(async () => {
      throw new TypeError('Failed to fetch');
    });

    await expect(createGift(api, { title: 'Buch', category: 'books' })).resolves.toMatchObject({
      ok: false,
      status: 502
    });
  });
});

describe('updateGift', () => {
  it('sends PUT to the idea', async () => {
    const { api, requests } = createApi(async () => jsonResponse(gift));

    await expect(
      updateGift(api, gift.id, { title: 'Raspberry Pi', category: 'tech' })
    ).resolves.toEqual({
      ok: true,
      data: gift
    });
    expect(requests[0].method).toBe('PUT');
    expect(new URL(requests[0].url).pathname).toBe(`/api/v1/gifts/${gift.id}`);
  });
});

describe('deleteGift', () => {
  it('deletes an idea with an empty success response', async () => {
    const { api, requests } = createApi(async () => new Response(null, { status: 204 }));

    await expect(deleteGift(api, gift.id)).resolves.toEqual({ ok: true, data: null });
    expect(requests[0].method).toBe('DELETE');
    expect(new URL(requests[0].url).pathname).toBe(`/api/v1/gifts/${gift.id}`);
  });

  it('returns 409 if a gifting still uses the idea', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'in use' }, 409));

    await expect(deleteGift(api, gift.id)).resolves.toEqual({
      ok: false,
      status: 409,
      message:
        'Die Idee wird von mindestens einer Beschenkung verwendet und kann nicht gelöscht werden.'
    });
  });
});
