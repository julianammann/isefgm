import { describe, expect, it, vi } from 'vitest';
import { ApiError, createGift, deleteGift, giftFromForm, listAllGifts } from './gifts';

const jsonResponse = (status: number, body?: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status });

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

describe('API-Aufrufe', () => {
  it('lädt Geschenkideen über mehrere Seiten bis zur Gesamtzahl', async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({
      id: `${index + 1}`,
      title: `Geschenk ${index + 1}`,
      category: 'other' as const,
      created_at: '2026-10-18T12:00:00Z',
      description: null,
      price_from: null,
      price_to: null,
      currency: null,
      people: [],
      occasions: []
    }));
    const secondPage = [{ ...firstPage[0], id: '101', title: 'Geschenk 101' }];
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(200, { items: firstPage, total: 101, limit: 100, offset: 0 })
      )
      .mockResolvedValueOnce(
        jsonResponse(200, { items: secondPage, total: 101, limit: 100, offset: 100 })
      );

    const gifts = await listAllGifts(fetch);

    expect(gifts).toEqual([...firstPage, ...secondPage]);
    expect(fetch).toHaveBeenNthCalledWith(1, '/api/v1/gifts?limit=100&offset=0', expect.anything());
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/gifts?limit=100&offset=100',
      expect.anything()
    );
  });

  it('createGift sendet POST mit JSON', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(201, { id: '1', title: 'Buch' }));
    await createGift(fetch, { title: 'Buch', category: 'other' });
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/gifts',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ title: 'Buch', category: 'other' })
      })
    );
  });

  it('deleteGift wirft ApiError bei 409 (Idee in Verwendung)', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(409, { detail: 'in use' }));
    await expect(deleteGift(fetch, '1')).rejects.toMatchObject({ status: 409 });
    await expect(deleteGift(fetch, '1')).rejects.toBeInstanceOf(ApiError);
  });
});
