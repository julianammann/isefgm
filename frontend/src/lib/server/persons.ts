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

export type Person = components['schemas']['PersonOut'];
export type PersonInput = components['schemas']['PersonIn'];

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
      api.GET('/api/v1/people', { params: { query: { offset: persons.length } } })
    );
    if (!page.ok) return page;
    persons.push(...page.data.items);
    if (page.data.items.length === 0 || persons.length >= page.data.total) {
      return { ok: true, data: persons };
    }
  }
}

/** Returns one person; 404 if the id is unknown or belongs to another account. */
export async function getPerson(api: Api, id: string): Promise<Result<Person>> {
  return send(api.GET('/api/v1/people/{person_id}', { params: { path: { person_id: id } } }));
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

/** Deletes a person and their birthday occasion; 404 if the id is unknown. */
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
