import { describe, expect, it, vi } from 'vitest';
import {
  giftingFromForm,
  groupByGift,
  listAllGiftings,
  toGiftingIn,
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

describe('listAllGiftings', () => {
  it('lädt alle Seiten', async () => {
    const page = (items: GiftingOut[], total: number) =>
      new Response(JSON.stringify({ items, total, limit: 1, offset: 0 }), { status: 200 });
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(page([given], 2))
      .mockResolvedValueOnce(page([{ ...given, id: 'g2' }], 2));

    const all = await listAllGiftings(fetch, 1);
    expect(all.map((g) => g.id)).toEqual(['g1', 'g2']);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
