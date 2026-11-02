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
import { isValidDate } from './dates';
import { listAll, send, sendEmpty, type Messages, type Result } from './result';

/** Payload for creating or updating a person. */
export type Person = components['schemas']['PersonOut'];
/** A person as returned by the API. */
export type PersonInput = components['schemas']['PersonIn'];
/** Field errors of the person form, keyed like `PersonInput`. */
export type PersonErrors = Partial<Record<keyof PersonInput, string>>;
/** What the person view shows (F-09): past gifts, open giftings with tasks, ideas and occasions. */
export type PersonOverview = components['schemas']['PersonOverviewOut'];

type Api = App.Locals['api'];

const messages: Messages = { 404: 'Person nicht gefunden.' };

/** Entries per list on the person view; separate from the list page size on purpose. */
const OVERVIEW_LIMIT = 200;

/** Returns all persons of the current account, sorted by name; reads every page of the list. */
export function listPersons(api: Api): Promise<Result<Person[]>> {
  return listAll(
    (offset) => api.GET('/api/v1/people', { params: { query: { offset, limit: PAGE_SIZE } } }),
    messages
  );
}

/** Returns one page of persons; `total` counts all entries, not only this page. */
export async function listPersonsPage(
  api: Api,
  page: number
): Promise<Result<{ items: Person[]; total: number }>> {
  const result = await send(
    api.GET('/api/v1/people', {
      params: { query: { limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } }
    }),
    messages
  );
  return result.ok
    ? { ok: true, data: { items: result.data.items, total: result.data.total } }
    : result;
}

/** Returns one person; 404 if the id is unknown or belongs to another account. */
export async function getPerson(api: Api, id: string): Promise<Result<Person>> {
  return send(
    api.GET('/api/v1/people/{person_id}', { params: { path: { person_id: id } } }),
    messages
  );
}

/**
 * Returns the person view (F-09) with up to `OVERVIEW_LIMIT` entries per list, each with its own
 * `total`; 404 if the id is unknown or belongs to another account.
 */
export async function getPersonOverview(api: Api, id: string): Promise<Result<PersonOverview>> {
  return send(
    api.GET('/api/v1/people/{person_id}/overview', {
      params: { path: { person_id: id }, query: { limit: OVERVIEW_LIMIT } }
    }),
    messages
  );
}

/** Creates a person and returns it with its new id. */
export async function createPerson(api: Api, input: PersonInput): Promise<Result<Person>> {
  return send(api.POST('/api/v1/people', { body: input }), messages);
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
    api.PUT('/api/v1/people/{person_id}', { params: { path: { person_id: id } }, body: input }),
    messages
  );
}

/** Deletes a person; 404 if the id is unknown. */
export function deletePerson(api: Api, id: string): Promise<Result<null>> {
  return sendEmpty(
    api.DELETE('/api/v1/people/{person_id}', { params: { path: { person_id: id } } }),
    messages
  );
}

/**
 * Reads and validates the person form. The backend remains the authority on validation.
 * Lengths count characters like the backend (`[...text]`); `.length` would count an emoji twice.
 */
export function parsePersonForm(form: FormData): { values: PersonInput; errors: PersonErrors } {
  const name = String(form.get('name') ?? '').trim();
  const birthday = String(form.get('birthday') ?? '').trim() || null;
  const relationship = String(form.get('relationship') ?? '').trim() || null;
  const notes = String(form.get('notes') ?? '').trim() || null;
  const errors: PersonErrors = {};

  if (!name) errors.name = 'Bitte gib einen Namen an.';
  else if ([...name].length > 100) errors.name = 'Der Name darf höchstens 100 Zeichen lang sein.';
  if (birthday && !isValidDate(birthday)) {
    errors.birthday = 'Bitte gib ein gültiges Datum an.';
  }
  if (relationship && [...relationship].length > 100) {
    errors.relationship = 'Die Beziehung darf höchstens 100 Zeichen lang sein.';
  }
  if (notes && [...notes].length > 2000) {
    errors.notes = 'Notizen dürfen höchstens 2000 Zeichen lang sein.';
  }
  return { values: { name, birthday, relationship, notes }, errors };
}
