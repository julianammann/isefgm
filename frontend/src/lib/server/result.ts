/**
 * Shared result type and request helpers for the data access modules.
 *
 * @module
 */

/** A failed data access call: HTTP status plus a German display message. */
export type Failure = { ok: false; status: number; message: string };

/** Outcome of a data access call; on failure carries the HTTP status and a display message. */
export type Result<T> = { ok: true; data: T } | Failure;

/** Display messages per HTTP status; the backend's own `detail` texts are English and not shown. */
export type Messages = Record<number, string>;

const sharedMessages: Messages = {
  401: 'Sitzung abgelaufen. Bitte erneut anmelden.',
  422: 'Die Eingaben sind ungültig.',
  502: 'Das Backend ist nicht erreichbar.'
};

/** Builds a failure for a status; looks in `messages` first, then in the shared texts. */
export function failure(status: number, messages: Messages): Failure {
  return {
    ok: false,
    status,
    message:
      messages[status] ??
      sharedMessages[status] ??
      'Unerwarteter Fehler. Bitte später erneut versuchen.'
  };
}

/** Awaits an API call and turns its response into a `Result`; network errors become 502. */
export async function send<T>(
  request: Promise<{ data?: T; response: Response }>,
  messages: Messages
): Promise<Result<T>> {
  try {
    const { data, response } = await request;
    if (!response.ok) return failure(response.status, messages);
    if (data === undefined) {
      return {
        ok: false,
        status: 502,
        message: 'Das Backend hat eine unerwartete Antwort geliefert.'
      };
    }
    return { ok: true, data };
  } catch (cause) {
    if (cause instanceof TypeError) return failure(502, messages);
    throw cause;
  }
}

/** Like `send` for calls without a response body, e.g. DELETE. */
export async function sendEmpty(
  request: Promise<{ response: Response }>,
  messages: Messages
): Promise<Result<null>> {
  try {
    const { response } = await request;
    return response.ok ? { ok: true, data: null } : failure(response.status, messages);
  } catch (cause) {
    if (cause instanceof TypeError) return failure(502, messages);
    throw cause;
  }
}

/** Reads every page of a paged list; `fetchPage` gets the offset of the next page. */
export async function listAll<T>(
  fetchPage: (
    offset: number
  ) => Promise<{ data?: { items: T[]; total: number }; response: Response }>,
  messages: Messages
): Promise<Result<T[]>> {
  const items: T[] = [];
  for (;;) {
    const page = await send(fetchPage(items.length), messages);
    if (!page.ok) return page;
    items.push(...page.data.items);
    if (page.data.items.length === 0 || items.length >= page.data.total) {
      return { ok: true, data: items };
    }
  }
}
