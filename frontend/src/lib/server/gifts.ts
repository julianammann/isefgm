/**
 * Gift ideas data access (F-04, F-05).
 *
 * Wraps the gift idea endpoints of the backend (`/api/v1/gifts`). All functions take the
 * typed API client from `locals.api` and return a `Result`, so routes never deal with
 * HTTP details themselves.
 *
 * @module
 */

import type { components } from '$lib/api/schema';

/** Payload for creating or updating a gift idea. */
export type GiftIn = components['schemas']['GiftIn'];
/** A gift idea as returned by the API. */
export type GiftOut = components['schemas']['GiftOut'];
/** Possible categories of a gift idea. */
export type GiftCategory = components['schemas']['GiftCategory'];

type Api = App.Locals['api'];

type Failure = { ok: false; status: number; message: string };

/** Outcome of a data access call; on failure carries the HTTP status and a display message. */
export type Result<T> = { ok: true; data: T } | Failure;

/** Display messages per HTTP status; the backend's own `detail` texts are English and not shown. */
const messages: Record<number, string> = {
  401: 'Sitzung abgelaufen. Bitte erneut anmelden.',
  404: 'Geschenkidee nicht gefunden.',
  409: 'Die Idee wird von mindestens einer Beschenkung verwendet und kann nicht gelöscht werden.',
  422: 'Die Eingaben sind ungültig.',
  502: 'Das Backend ist nicht erreichbar.'
};

function fail(status: number): Failure {
  return {
    ok: false,
    status,
    message: messages[status] ?? 'Unerwarteter Fehler. Bitte später erneut versuchen.'
  };
}

/** Awaits an API call and turns its response into a `Result`; network errors become 502. */
async function send<T>(request: Promise<{ data?: T; response: Response }>): Promise<Result<T>> {
  try {
    const { data, response } = await request;
    if (!response.ok) return fail(response.status);
    if (data === undefined) {
      return {
        ok: false,
        status: 502,
        message: 'Das Backend hat eine unerwartete Antwort geliefert.'
      };
    }
    return { ok: true, data };
  } catch (cause) {
    if (cause instanceof TypeError) return fail(502);
    throw cause;
  }
}

/** Returns all gift ideas of the current account, newest first; reads every page of the list. */
export async function listGifts(api: Api): Promise<Result<GiftOut[]>> {
  const gifts: GiftOut[] = [];
  for (;;) {
    const page = await send(
      api.GET('/api/v1/gifts', { params: { query: { offset: gifts.length } } })
    );
    if (!page.ok) return page;
    gifts.push(...page.data.items);
    if (page.data.items.length === 0 || gifts.length >= page.data.total) {
      return { ok: true, data: gifts };
    }
  }
}

/** Creates a gift idea and returns it with its new id. */
export async function createGift(api: Api, input: GiftIn): Promise<Result<GiftOut>> {
  return send(api.POST('/api/v1/gifts', { body: input }));
}

/**
 * Replaces all data of an existing gift idea, including its links; 404 if the id is unknown.
 * Fields left out of `input` are reset to null, their default or an empty list by the backend.
 */
export async function updateGift(api: Api, id: string, input: GiftIn): Promise<Result<GiftOut>> {
  return send(
    api.PUT('/api/v1/gifts/{gift_id}', { params: { path: { gift_id: id } }, body: input })
  );
}

/** Deletes a gift idea; 404 if the id is unknown, 409 if a gifting still uses it. */
export async function deleteGift(api: Api, id: string): Promise<Result<null>> {
  try {
    const { response } = await api.DELETE('/api/v1/gifts/{gift_id}', {
      params: { path: { gift_id: id } }
    });
    return response.ok ? { ok: true, data: null } : fail(response.status);
  } catch (cause) {
    if (cause instanceof TypeError) return fail(502);
    throw cause;
  }
}

// ── Form mapping ────────────────────────────────────────────────

/** Returns the trimmed form value, or null if it is empty; the backend stores empty optional fields as null. */
export function text(form: FormData, name: string): string | null {
  const v = form.get(name);
  return typeof v === 'string' && v.trim() !== '' ? v.trim() : null;
}

/** Returns all non-empty values of a multi-value form field, e.g. checked checkboxes. */
export function ids(form: FormData, name: string): string[] {
  return form.getAll(name).filter((v): v is string => typeof v === 'string' && v !== '');
}

/** Maps the gift idea form to `GiftIn`; always maps every field, because PUT replaces all of them. */
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
