import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import type { GiftOut } from './gifts';
import { createGift, deleteGift, giftFromForm, listGifts, updateGift } from './gifts';

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
  it('benötigt nur den Titel und setzt Standardwerte', () => {
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

  it('wandelt Dezimalkomma in Punkt', () => {
    const f = new FormData();
    f.set('title', 'Buch');
    f.set('price_from', '10,50');
    expect(giftFromForm(f).price_from).toBe('10.50');
  });

  it('normalisiert den Währungscode auf Großbuchstaben', () => {
    const f = new FormData();
    f.set('title', 'Buch');
    f.set('price_from', '10');
    f.set('currency', 'eur');
    expect(giftFromForm(f).currency).toBe('EUR');
  });
});

describe('listGifts', () => {
  it('lädt alle Seiten mit der Anzahl geladener Ideen als nächstem Offset', async () => {
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

  it('liefert den Backend-Fehler einer fehlgeschlagenen Seite', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'Unauthorized' }, 401));

    await expect(listGifts(api)).resolves.toEqual({
      ok: false,
      status: 401,
      message: 'Sitzung abgelaufen. Bitte erneut anmelden.'
    });
  });
});

describe('createGift', () => {
  it('sendet POST mit JSON und liefert die angelegte Idee', async () => {
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

  it('wandelt einen Netzwerkfehler in 502', async () => {
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
  it('sendet PUT an die Idee', async () => {
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
  it('löscht eine Idee bei leerer Erfolgsantwort', async () => {
    const { api, requests } = createApi(async () => new Response(null, { status: 204 }));

    await expect(deleteGift(api, gift.id)).resolves.toEqual({ ok: true, data: null });
    expect(requests[0].method).toBe('DELETE');
    expect(new URL(requests[0].url).pathname).toBe(`/api/v1/gifts/${gift.id}`);
  });

  it('liefert 409, wenn eine Beschenkung die Idee verwendet', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'in use' }, 409));

    await expect(deleteGift(api, gift.id)).resolves.toEqual({
      ok: false,
      status: 409,
      message:
        'Die Idee wird von mindestens einer Beschenkung verwendet und kann nicht gelöscht werden.'
    });
  });
});
