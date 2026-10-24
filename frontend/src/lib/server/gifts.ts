import type { components } from '$lib/api/schema'; // Pfad an Lage von schema.d.ts anpassen

export type GiftIn = components['schemas']['GiftIn'];
export type GiftOut = components['schemas']['GiftOut'];
export type GiftCategory = components['schemas']['GiftCategory'];
type GiftPage = components['schemas']['Page_GiftOut_'];
type Fetch = typeof globalThis.fetch;

const BASE = '/api/v1/gifts';

export class ApiError extends Error {
  constructor(public readonly status: number) {
    super(`API-Fehler ${status}`);
  }
}

/** Request-Helper – an das Muster aus persons.ts angleichen, falls dort bereits einer existiert. */
export async function api<T>(fetch: Fetch, url: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: init.body ? { 'content-type': 'application/json' } : undefined
  });
  if (!res.ok) throw new ApiError(res.status);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

/** Loads every gift page so the overview does not silently stop at the first 100 ideas. */
export async function listAllGifts(fetch: Fetch, pageSize = 100): Promise<GiftOut[]> {
  const items: GiftOut[] = [];
  for (;;) {
    const page = await api<GiftPage>(fetch, `${BASE}?limit=${pageSize}&offset=${items.length}`);
    items.push(...page.items);
    if (page.items.length === 0 || items.length >= page.total) return items;
  }
}

export const createGift = (fetch: Fetch, body: GiftIn) =>
  api<GiftOut>(fetch, BASE, { method: 'POST', body: JSON.stringify(body) });

export const updateGift = (fetch: Fetch, id: string, body: GiftIn) =>
  api<GiftOut>(fetch, `${BASE}/${id}`, { method: 'PUT', body: JSON.stringify(body) });

export const deleteGift = (fetch: Fetch, id: string) =>
  api<void>(fetch, `${BASE}/${id}`, { method: 'DELETE' });

// ── Formular-Mapping ────────────────────────────────────────────

/** Leerer Wert → null (Backend speichert leere optionale Felder als null). */
export function text(form: FormData, name: string): string | null {
  const v = form.get(name);
  return typeof v === 'string' && v.trim() !== '' ? v.trim() : null;
}

export function ids(form: FormData, name: string): string[] {
  return form.getAll(name).filter((v): v is string => typeof v === 'string' && v !== '');
}

/** PUT ersetzt alle Felder – daher immer das vollständige Formular abbilden. */
export function giftFromForm(form: FormData): GiftIn {
  return {
    title: text(form, 'title') ?? '',
    description: text(form, 'description'),
    category: (text(form, 'category') ?? 'other') as GiftCategory,
    price_from: text(form, 'price_from')?.replace(',', '.') ?? null,
    price_to: text(form, 'price_to')?.replace(',', '.') ?? null,
    currency: text(form, 'currency')?.toUpperCase() ?? null,
    person_ids: ids(form, 'person_ids'),
    occasion_ids: ids(form, 'occasion_ids')
  };
}
