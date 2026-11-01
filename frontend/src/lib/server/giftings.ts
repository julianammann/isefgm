/**
 * Giftings data access (F-06).
 *
 * Wraps the gifting endpoints of the backend (`/api/v1/giftings`). All functions take the
 * typed API client from `locals.api` and return a `Result`, so routes never deal with
 * HTTP details themselves.
 *
 * @module
 */

import type { components } from '$lib/api/schema';
import { PAGE_SIZE } from '$lib/pagination';
import { ids, text } from './gifts';

/** Payload for creating or updating a gifting. */
export type GiftingIn = components['schemas']['GiftingIn'];
/** A gifting as returned by the API. */
export type GiftingOut = components['schemas']['GiftingOut'];
/** Progress of a gifting: `idea`, `planned`, `acquired` or `given`. */
export type GiftingStatus = components['schemas']['GiftingStatus'];

type Api = App.Locals['api'];

type Failure = { ok: false; status: number; message: string };

/** Outcome of a data access call; on failure carries the HTTP status and a display message. */
export type Result<T> = { ok: true; data: T } | Failure;

/** Display messages per HTTP status; the backend's own `detail` texts are English and not shown. */
const messages: Record<number, string> = {
  401: 'Sitzung abgelaufen. Bitte erneut anmelden.',
  404: 'Beschenkung nicht gefunden.',
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

/** Returns all giftings of the current account, newest first; reads every page of the list. */
export async function listGiftings(api: Api): Promise<Result<GiftingOut[]>> {
  const giftings: GiftingOut[] = [];
  for (;;) {
    const page = await send(
      api.GET('/api/v1/giftings', {
        params: { query: { offset: giftings.length, limit: PAGE_SIZE } }
      })
    );
    if (!page.ok) return page;
    giftings.push(...page.data.items);
    if (page.data.items.length === 0 || giftings.length >= page.data.total) {
      return { ok: true, data: giftings };
    }
  }
}

/** Returns one gifting; 404 if the id is unknown or belongs to another account. */
export async function getGifting(api: Api, id: string): Promise<Result<GiftingOut>> {
  return send(api.GET('/api/v1/giftings/{gifting_id}', { params: { path: { gifting_id: id } } }));
}

/** Creates a gifting from a gift idea and returns it with its new id. */
export async function createGifting(api: Api, input: GiftingIn): Promise<Result<GiftingOut>> {
  return send(api.POST('/api/v1/giftings', { body: input }));
}

/**
 * Replaces all data of an existing gifting, including its recipients; 404 if the id is unknown.
 * Fields left out of `input` are reset to null, their default or an empty list by the backend.
 */
export async function updateGifting(
  api: Api,
  id: string,
  input: GiftingIn
): Promise<Result<GiftingOut>> {
  return send(
    api.PUT('/api/v1/giftings/{gifting_id}', {
      params: { path: { gifting_id: id } },
      body: input
    })
  );
}

/** Deletes a gifting; the idea, the people and the occasion stay. 404 if the id is unknown. */
export async function deleteGifting(api: Api, id: string): Promise<Result<null>> {
  try {
    const { response } = await api.DELETE('/api/v1/giftings/{gifting_id}', {
      params: { path: { gifting_id: id } }
    });
    return response.ok ? { ok: true, data: null } : fail(response.status);
  } catch (cause) {
    if (cause instanceof TypeError) return fail(502);
    throw cause;
  }
}

// ── Helpers ─────────────────────────────────────────────────────

/** Groups giftings by gift idea id, so each idea can list its own giftings. */
export function groupByGift(giftings: GiftingOut[]): Record<string, GiftingOut[]> {
  const grouped: Record<string, GiftingOut[]> = {};
  for (const g of giftings) (grouped[g.gift.id] ??= []).push(g);
  return grouped;
}

/** Turns a gifting into a complete `GiftingIn`; PUT replaces all fields, `patch` changes only the given ones. */
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

/** Maps the gifting form to `GiftingIn` for the given gift idea; the status defaults to `idea`. */
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

type GiftingFieldErrors = Partial<Record<keyof GiftingIn, string>>;

const GIFTING_STATUSES = ['idea', 'planned', 'acquired', 'given'] as const;

/**
 * Reads and validates the gifting form. A given gifting needs recipients, an occasion, its
 * date and the day it was given, like the backend checks. The backend remains the authority.
 */
export function parseGiftingForm(form: FormData): {
  values: GiftingIn;
  errors: GiftingFieldErrors;
} {
  const status = String(form.get('status') ?? '');
  const values = giftingFromForm(form, String(form.get('gift_id') ?? ''));
  const errors: GiftingFieldErrors = {};

  if (!values.gift_id) errors.gift_id = 'Keine Geschenkidee ausgewählt.';
  if (!(GIFTING_STATUSES as readonly string[]).includes(status)) {
    errors.status = 'Bitte wähle einen gültigen Status.';
  }
  if (values.occasion_date && Number.isNaN(Date.parse(values.occasion_date))) {
    errors.occasion_date = 'Bitte gib ein gültiges Datum an.';
  }
  if (values.given_on && Number.isNaN(Date.parse(values.given_on))) {
    errors.given_on = 'Bitte gib ein gültiges Datum an.';
  }
  if (values.status === 'given') {
    if (!values.person_ids?.length) {
      errors.person_ids = 'Für „Verschenkt“ bitte mindestens eine Person auswählen.';
    }
    if (!values.occasion_id) errors.occasion_id = 'Für „Verschenkt“ bitte einen Anlass wählen.';
    if (!values.occasion_date) {
      errors.occasion_date ??= 'Für „Verschenkt“ bitte den Anlasstermin angeben.';
    }
    if (!values.given_on) errors.given_on ??= 'Für „Verschenkt“ bitte das Verschenkdatum angeben.';
  }
  const birthdayError = birthdayRecipientError(
    values,
    String(form.get('birthday_occasion_id') ?? '') || null
  );
  if (birthdayError) errors.person_ids ??= birthdayError;
  return { values, errors };
}

/** A gifting at the birthday occasion needs exactly one distinct recipient, like the backend checks. */
export function birthdayRecipientError(
  values: Pick<GiftingIn, 'occasion_id' | 'person_ids'>,
  birthdayOccasionId: string | null
): string | undefined {
  if (!birthdayOccasionId || values.occasion_id !== birthdayOccasionId) return undefined;
  return new Set(values.person_ids).size === 1
    ? undefined
    : 'Für einen Geburtstag bitte genau eine Person auswählen.';
}
