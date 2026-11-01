/**
 * Persons data access (F-02).
 *
 * Wraps the people endpoints of the backend (`/api/v1/people`). All functions take the
 * typed API client from `locals.api` and return a `Result`, so routes never deal with
 * HTTP details themselves.
 *
 * @module
 */

import type { components } from '$lib/api/schema';
import { PAGE_SIZE } from '$lib/pagination';

/** Payload for creating or updating a person. */
export type Person = components['schemas']['PersonOut'];
/** A person as returned by the API. */
export type PersonInput = components['schemas']['PersonIn'];
/** Field errors of the person form, keyed like `PersonInput`. */
export type PersonErrors = Partial<Record<keyof PersonInput, string>>;
/** What the person view shows (F-09): past gifts, open giftings with tasks, ideas and occasions. */
export type PersonOverview = components['schemas']['PersonOverviewOut'];

type Api = App.Locals['api'];

type Failure = { ok: false; status: number; message: string };

/** Outcome of a data access call; on failure carries the HTTP status and a display message. */
export type Result<T> = { ok: true; data: T } | Failure;

/** Display messages per HTTP status; the backend's own `detail` texts are English and not shown. */
const messages: Record<number, string> = {
  401: 'Sitzung abgelaufen. Bitte erneut anmelden.',
  404: 'Person nicht gefunden.',
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

/** Returns all persons of the current account, sorted by name; reads every page of the list. */
export async function listPersons(api: Api): Promise<Result<Person[]>> {
  const persons: Person[] = [];
  for (;;) {
    const page = await send(
      api.GET('/api/v1/people', { params: { query: { offset: persons.length, limit: PAGE_SIZE } } })
    );
    if (!page.ok) return page;
    persons.push(...page.data.items);
    if (page.data.items.length === 0 || persons.length >= page.data.total) {
      return { ok: true, data: persons };
    }
  }
}

/** Returns one page of persons; `total` counts all entries, not only this page. */
export async function listPersonsPage(
  api: Api,
  page: number
): Promise<Result<{ items: Person[]; total: number }>> {
  const result = await send(
    api.GET('/api/v1/people', {
      params: { query: { limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } }
    })
  );
  return result.ok
    ? { ok: true, data: { items: result.data.items, total: result.data.total } }
    : result;
}

/** Returns one person; 404 if the id is unknown or belongs to another account. */
export async function getPerson(api: Api, id: string): Promise<Result<Person>> {
  return send(api.GET('/api/v1/people/{person_id}', { params: { path: { person_id: id } } }));
}

/**
 * Returns the person view (F-09) with up to `PAGE_SIZE` entries per list, each with its own
 * `total`; 404 if the id is unknown or belongs to another account.
 */
export async function getPersonOverview(api: Api, id: string): Promise<Result<PersonOverview>> {
  return send(
    api.GET('/api/v1/people/{person_id}/overview', {
      params: { path: { person_id: id }, query: { limit: PAGE_SIZE } }
    })
  );
}

/** Creates a person and returns it with its new id. */
export async function createPerson(api: Api, input: PersonInput): Promise<Result<Person>> {
  return send(api.POST('/api/v1/people', { body: input }));
}

/**
 * Replaces all data of an existing person; 404 if the id is unknown.
 * Fields left out of `input` are reset to null by the backend.
 */
export async function updatePerson(
  api: Api,
  id: string,
  input: PersonInput
): Promise<Result<Person>> {
  return send(
    api.PUT('/api/v1/people/{person_id}', { params: { path: { person_id: id } }, body: input })
  );
}

/** Deletes a person; 404 if the id is unknown. */
export async function deletePerson(api: Api, id: string): Promise<Result<null>> {
  try {
    const { response } = await api.DELETE('/api/v1/people/{person_id}', {
      params: { path: { person_id: id } }
    });
    return response.ok ? { ok: true, data: null } : fail(response.status);
  } catch (cause) {
    if (cause instanceof TypeError) return fail(502);
    throw cause;
  }
}

/** Reads and validates the person form. The backend remains the authority on validation. */
export function parsePersonForm(form: FormData): { values: PersonInput; errors: PersonErrors } {
  const name = String(form.get('name') ?? '').trim();
  const birthday = String(form.get('birthday') ?? '').trim() || null;
  const relationship = String(form.get('relationship') ?? '').trim() || null;
  const notes = String(form.get('notes') ?? '').trim() || null;
  const errors: PersonErrors = {};

  if (!name) errors.name = 'Bitte gib einen Namen an.';
  else if (name.length > 100) errors.name = 'Der Name darf höchstens 100 Zeichen lang sein.';
  if (birthday && Number.isNaN(Date.parse(birthday))) {
    errors.birthday = 'Bitte gib ein gültiges Datum an.';
  }
  if (relationship && relationship.length > 100) {
    errors.relationship = 'Die Beziehung darf höchstens 100 Zeichen lang sein.';
  }
  if (notes && notes.length > 2000) {
    errors.notes = 'Notizen dürfen höchstens 2000 Zeichen lang sein.';
  }
  return { values: { name, birthday, relationship, notes }, errors };
}
