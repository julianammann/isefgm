/**
 * Gift idea links data access.
 *
 * Wraps the link endpoints of the backend (`/api/v1/links`).
 *
 * @module
 */

import type { components } from '$lib/api/schema';
import { text } from './gifts';
import { labelError } from './notes';
import { listAll, send, sendEmpty, type Messages, type Result } from './result';

/** Payload for creating or updating a link. */
export type LinkIn = components['schemas']['LinkIn'];
/** A link as returned by the API. */
export type LinkOut = components['schemas']['LinkOut'];
/** Field errors of the link form, keyed by field name. */
export type LinkErrors = Partial<Record<'label' | 'url', string>>;

type Api = App.Locals['api'];

const messages: Messages = { 404: 'Link nicht gefunden.' };

/** Returns all links of a gift idea; reads every page of the list. */
export function listLinks(api: Api, giftId: string): Promise<Result<LinkOut[]>> {
  return listAll(
    (offset) =>
      api.GET('/api/v1/links', { params: { query: { gift_id: giftId, limit: 200, offset } } }),
    messages
  );
}

/** Creates a link and returns it with its new id. */
export function createLink(api: Api, input: LinkIn): Promise<Result<LinkOut>> {
  return send(api.POST('/api/v1/links', { body: input }), messages);
}

/** Replaces a link; 404 if the id is unknown. */
export function updateLink(api: Api, id: string, input: LinkIn): Promise<Result<LinkOut>> {
  return send(
    api.PUT('/api/v1/links/{link_id}', { params: { path: { link_id: id } }, body: input }),
    messages
  );
}

/** Deletes a link; 404 if the id is unknown. */
export function deleteLink(api: Api, id: string): Promise<Result<null>> {
  return sendEmpty(
    api.DELETE('/api/v1/links/{link_id}', { params: { path: { link_id: id } } }),
    messages
  );
}

/** Whether a value is an absolute `http:` or `https:` URL with a host. */
export function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return (url.protocol === 'http:' || url.protocol === 'https:') && url.hostname !== '';
  } catch {
    return false;
  }
}

function urlError(value: string): string | undefined {
  if (value === '') return 'Bitte gib eine Adresse an.';
  if (value.length > 2048) return 'Die Adresse darf höchstens 2048 Zeichen lang sein.';
  if (!isHttpUrl(value)) return 'Bitte gib eine vollständige Adresse mit http:// oder https:// an.';
  return undefined;
}

/** Maps the link form to `LinkIn` and validates it; `values` are trimmed, empty ones become ''. */
export function parseLinkForm(
  form: FormData,
  giftId: string
): { values: LinkIn; errors: LinkErrors } {
  const values: LinkIn = {
    gift_id: giftId,
    label: text(form, 'label') ?? '',
    url: text(form, 'url') ?? ''
  };
  const errors: LinkErrors = {};
  const label = labelError(values.label);
  const url = urlError(values.url);
  if (label) errors.label = label;
  if (url) errors.url = url;
  return { values, errors };
}
