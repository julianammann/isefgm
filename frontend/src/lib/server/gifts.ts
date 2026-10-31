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
import { PAGE_SIZE } from '$lib/pagination';

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

/** Returns one page of gift ideas; `total` counts all entries, not only this page. */
export async function listGiftsPage(
  api: Api,
  page: number
): Promise<Result<{ items: GiftOut[]; total: number }>> {
  const result = await send(
    api.GET('/api/v1/gifts', {
      params: { query: { limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } }
    })
  );
  return result.ok
    ? { ok: true, data: { items: result.data.items, total: result.data.total } }
    : result;
}

/** Returns one gift idea; 404 if the id is unknown or belongs to another account. */
export async function getGift(api: Api, id: string): Promise<Result<GiftOut>> {
  return send(api.GET('/api/v1/gifts/{gift_id}', { params: { path: { gift_id: id } } }));
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

/**
 * Whether a price fits the backend's `Numeric(10, 2)` column: not negative, at most
 * 8 digits before and 2 after the decimal point. Expects the point form from `giftFromForm`,
 * so a thousands separator like `1.000,50` is rejected.
 */
export function isPrice(value: string): boolean {
  return /^\d{1,8}(\.\d{1,2})?$/.test(value);
}

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

type FieldErrors = Partial<Record<keyof GiftIn, string>>;

/** Reads and validates the gift idea form. The backend remains the authority on validation. */
export function parseGiftForm(form: FormData): { values: GiftIn; errors: FieldErrors } {
  const values = giftFromForm(form);
  const priceFrom = values.price_from === null ? null : String(values.price_from);
  const priceTo = values.price_to === null ? null : String(values.price_to);
  const errors: FieldErrors = {};
  const invalidPrice = 'Bitte gib einen Preis mit höchstens zwei Nachkommastellen an, z. B. 10,99.';

  if (!values.title) errors.title = 'Bitte gib einen Titel an.';
  else if (values.title.length > 200) {
    errors.title = 'Der Titel darf höchstens 200 Zeichen lang sein.';
  }
  if (values.description && values.description.length > 2000) {
    errors.description = 'Die Beschreibung darf höchstens 2000 Zeichen lang sein.';
  }
  if (priceFrom !== null && !isPrice(priceFrom)) errors.price_from = invalidPrice;
  if (priceTo !== null && !isPrice(priceTo)) errors.price_to = invalidPrice;
  else if (
    priceFrom !== null &&
    priceTo !== null &&
    !errors.price_from &&
    Number(priceFrom) > Number(priceTo)
  ) {
    errors.price_to = '„Preis bis“ darf nicht kleiner als „Preis von“ sein.';
  }
  if (values.currency && !/^[A-Z]{3}$/.test(values.currency)) {
    errors.currency = 'Bitte gib einen Währungscode aus drei Buchstaben an, z. B. EUR.';
  }
  return { values, errors };
}
