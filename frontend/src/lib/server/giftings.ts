import type { components } from '$lib/api/schema'; // Pfad an Lage von schema.d.ts anpassen
import { api, ids, text } from './gifts';

export type GiftingIn = components['schemas']['GiftingIn'];
export type GiftingOut = components['schemas']['GiftingOut'];
export type GiftingStatus = components['schemas']['GiftingStatus'];
type GiftingPage = components['schemas']['Page_GiftingOut_'];
type Fetch = typeof globalThis.fetch;

const BASE = '/api/v1/giftings';

/** Alle Beschenkungen laden (Paging). Die API hat bisher keinen gift_id-Filter. */
export async function listAllGiftings(fetch: Fetch, pageSize = 100): Promise<GiftingOut[]> {
  const items: GiftingOut[] = [];
  for (;;) {
    const page = await api<GiftingPage>(fetch, `${BASE}?limit=${pageSize}&offset=${items.length}`);
    items.push(...page.items);
    if (page.items.length === 0 || items.length >= page.total) return items;
  }
}

export const getGifting = (fetch: Fetch, id: string) => api<GiftingOut>(fetch, `${BASE}/${id}`);

export const createGifting = (fetch: Fetch, body: GiftingIn) =>
  api<GiftingOut>(fetch, BASE, { method: 'POST', body: JSON.stringify(body) });

export const updateGifting = (fetch: Fetch, id: string, body: GiftingIn) =>
  api<GiftingOut>(fetch, `${BASE}/${id}`, { method: 'PUT', body: JSON.stringify(body) });

export const deleteGifting = (fetch: Fetch, id: string) =>
  api<void>(fetch, `${BASE}/${id}`, { method: 'DELETE' });

// ── Hilfsfunktionen ─────────────────────────────────────────────

/** Beschenkungen je Idee gruppieren (für die Anzeige unter der jeweiligen Idee). */
export function groupByGift(giftings: GiftingOut[]): Record<string, GiftingOut[]> {
  const grouped: Record<string, GiftingOut[]> = {};
  for (const g of giftings) (grouped[g.gift.id] ??= []).push(g);
  return grouped;
}

/** Aktuellen Stand in GiftingIn überführen; PUT ersetzt alle Felder, `patch` ändert nur das Gewünschte. */
export function toGiftingIn(current: GiftingOut, patch: Partial<GiftingIn> = {}): GiftingIn {
  return {
    gift_id: current.gift.id,
    person_ids: current.people.map((p) => p.id),
    occasion_id: current.occasion?.id ?? null,
    occasion_date: current.occasion_date,
    given_on: current.given_on,
    status: current.status,
    ...patch
  };
}

export function giftingFromForm(form: FormData, giftId: string): GiftingIn {
  return {
    gift_id: giftId,
    person_ids: ids(form, 'person_ids'),
    occasion_id: text(form, 'occasion_id'),
    occasion_date: text(form, 'occasion_date'),
    given_on: text(form, 'given_on'),
    status: (text(form, 'status') ?? 'idea') as GiftingStatus
  };
}
