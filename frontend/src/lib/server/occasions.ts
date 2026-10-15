/**
 * Occasions data access (F-03).
 *
 * @module
 */

import type { components } from '$lib/api/schema';

/** Payload for creating or updating an occasion. */
export type Occasion = components['schemas']['OccasionOut'];
/** A occasion as returned by the API. */
export type OccasionInput = components['schemas']['OccasionIn'];
/** A occasion type as returned by the API. */
export type OccasionType = components['schemas']['OccasionTypeOut'];

type Api = App.Locals['api'];

type Failure = { ok: false; status: number; message: string };

/** Outcome of a data access call; on failure carries the HTTP status and a display message. */
export type Result<T> = { ok: true; data: T } | Failure;

/** Display messages per HTTP status; the backend's own `detail` texts are English and not shown. */
const messages: Record<number, string> = {
  401: 'Sitzung abgelaufen. Bitte erneut anmelden.',
  404: 'Anlass nicht gefunden.',
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

/** Returns all occasions of the current account, sorted by date; reads every page of the list. */
export async function listOccasions(api: Api): Promise<Result<Occasion[]>> {
  const occasions: Occasion[] = [];
  for (;;) {
    const page = await send(
      api.GET('/api/v1/occasions', { params: { query: { offset: occasions.length } } })
    );
    if (!page.ok) return page;
    occasions.push(...page.data.items);
    if (page.data.items.length === 0 || occasions.length >= page.data.total) {
      return { ok: true, data: occasions };
    }
  }
}

/** Returns all occasion types of the current account. */
export async function listOccasionTypes(api: Api): Promise<Result<OccasionType[]>> {
  const types: OccasionType[] = [];
  for (;;) {
    const page = await send(
      api.GET('/api/v1/occasion-types', { params: { query: { offset: types.length } } })
    );
    if (!page.ok) return page;
    types.push(...page.data.items);
    if (page.data.items.length === 0 || types.length >= page.data.total) {
      return { ok: true, data: types };
    }
  }
}

/** Returns one occasion; 404 if not found. */
export async function getOccasion(api: Api, id: string): Promise<Result<Occasion>> {
  return send(
    api.GET('/api/v1/occasions/{occasion_id}', { params: { path: { occasion_id: id } } })
  );
}

/** Creates a new occasion. */
export async function createOccasion(api: Api, input: OccasionInput): Promise<Result<Occasion>> {
  return send(api.POST('/api/v1/occasions', { body: input }));
}

/** Updates an existing occasion. */
export async function updateOccasion(
  api: Api,
  id: string,
  input: OccasionInput
): Promise<Result<Occasion>> {
  return send(
    api.PUT('/api/v1/occasions/{occasion_id}', {
      params: { path: { occasion_id: id } },
      body: input
    })
  );
}

/** Deletes an occasion. */
export async function deleteOccasion(api: Api, id: string): Promise<Result<null>> {
  try {
    const { response } = await api.DELETE('/api/v1/occasions/{occasion_id}', {
      params: { path: { occasion_id: id } }
    });
    return response.ok ? { ok: true, data: null } : fail(response.status);
  } catch (cause) {
    if (cause instanceof TypeError) return fail(502);
    throw cause;
  }
}
