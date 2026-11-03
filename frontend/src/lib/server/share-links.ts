/**
 * Share link data access (F-14).
 *
 * Wraps the share link endpoints of the backend: managing links as their owner
 * (`/api/v1/share-links`) and opening the read-only view by token (`/api/v1/shared/{token}`).
 *
 * @module
 */

import { fail } from '@sveltejs/kit';

import type { components } from '#lib/api/schema.js';
import { berlinDate, endOfBerlinDay } from '#lib/expiry.js';
import { PAGE_SIZE } from '#lib/pagination.js';
import { isValidDate } from './dates';
import { listAll, send, sendEmpty, type Messages, type Result } from './result';

/** A share link as its owner sees it, without the token. */
export type ShareLink = components['schemas']['ShareLinkOut'];
/** A new share link with its token, which the backend returns only this once. */
export type CreatedShareLink = components['schemas']['ShareLinkCreated'];
/** Payload for creating or updating a share link. */
export type ShareLinkInput = components['schemas']['ShareLinkIn'];
/** What a valid share link shows: the chosen people and their gift ideas. */
export type SharedList = components['schemas']['SharedListOut'];

/** What the share link form holds; the expiry is a calendar day, empty for no expiry. */
export type ShareLinkValues = { person_ids: string[]; expires_on: string | null };
/** Field errors of the share link form. */
export type ShareLinkErrors = Partial<Record<keyof ShareLinkValues, string>>;

type Api = App.Locals['api'];

const messages: Messages = {
  // 400 only comes for an expiry in the past; the form checks that too.
  400: 'Das Ablaufdatum darf nicht in der Vergangenheit liegen.',
  404: 'Teilen-Link oder Person nicht gefunden.'
};

/** Returns all share links of the current account, newest first; reads every page. */
export function listShareLinks(api: Api): Promise<Result<ShareLink[]>> {
  return listAll(
    (offset) => api.GET('/api/v1/share-links', { params: { query: { offset, limit: PAGE_SIZE } } }),
    messages
  );
}

/** Returns one share link of the current account, without its token. */
export function getShareLink(api: Api, id: string): Promise<Result<ShareLink>> {
  return send(
    api.GET('/api/v1/share-links/{share_link_id}', {
      params: { path: { share_link_id: id } }
    }),
    messages
  );
}

/** Creates a share link and returns it with its token, the only time the token is returned. */
export function createShareLink(
  api: Api,
  input: ShareLinkInput
): Promise<Result<CreatedShareLink>> {
  return send(api.POST('/api/v1/share-links', { body: input }), messages);
}

/** Replaces the people, expiry and active flag of a share link; the token stays the same. */
export function updateShareLink(
  api: Api,
  id: string,
  input: ShareLinkInput
): Promise<Result<ShareLink>> {
  return send(
    api.PUT('/api/v1/share-links/{share_link_id}', {
      params: { path: { share_link_id: id } },
      body: input
    }),
    messages
  );
}

/** Deletes a share link for good; it no longer opens. */
export function deleteShareLink(api: Api, id: string): Promise<Result<null>> {
  return sendEmpty(
    api.DELETE('/api/v1/share-links/{share_link_id}', {
      params: { path: { share_link_id: id } }
    }),
    messages
  );
}

/**
 * Opens the read-only view behind a token, without a login. An unknown, deactivated or expired
 * token gives the same 404, so the page cannot tell them apart either.
 */
export function getSharedList(api: Api, token: string): Promise<Result<SharedList>> {
  return send(api.GET('/api/v1/shared/{token}', { params: { path: { token } } }), {
    404: 'Dieser Link ist nicht gültig oder nicht mehr aktiv.'
  });
}

/** Whether a link opens at `now`: active and not expired. */
export function isOpen(link: Pick<ShareLink, 'active' | 'expires_at'>, now: Date): boolean {
  return link.active && (link.expires_at === null || new Date(link.expires_at) > now);
}

/**
 * Reads and validates the share link form and builds the backend's `expires_at`. The expiry
 * is a day in German time, valid to its end. An edit that keeps the day sends the stored instant
 * again (`current_expires_at`), so an expired link can still be changed otherwise, like the
 * backend allows. The backend remains the authority on validation.
 */
export function parseShareLinkForm(
  form: FormData,
  now = new Date()
): { values: ShareLinkValues; expires_at: string | null; errors: ShareLinkErrors } {
  const person_ids = [...new Set(form.getAll('person_ids').map(String).filter(Boolean))];
  const expires_on = String(form.get('expires_on') ?? '').trim() || null;
  const current = String(form.get('current_expires_at') ?? '') || null;
  const unchanged = current !== null && expires_on === berlinDate(current);
  const errors: ShareLinkErrors = {};

  if (person_ids.length === 0) errors.person_ids = 'Bitte wähle mindestens eine Person aus.';
  else if (person_ids.length > 100) errors.person_ids = 'Höchstens 100 Personen pro Link.';
  if (expires_on !== null && !isValidDate(expires_on)) {
    errors.expires_on = 'Bitte gib ein gültiges Datum an.';
  } else if (expires_on !== null && !unchanged && expires_on < berlinDate(now)) {
    errors.expires_on = 'Das Datum darf nicht in der Vergangenheit liegen.';
  }

  const expires_at = expires_on === null ? null : unchanged ? current : endOfBerlinDay(expires_on);
  return { values: { person_ids, expires_on }, expires_at, errors };
}

/**
 * The `share` form action of the person pages: validates the form and creates a share link.
 * Returns the link's URL instead of redirecting, because the token comes back only this once and
 * must not travel in a redirect URL. An expiry the backend sees in the past shows at its field.
 */
export async function shareAction(api: Api, form: FormData, origin: string) {
  const scope = 'share' as const;
  const { values, expires_at, errors } = parseShareLinkForm(form);
  if (Object.keys(errors).length) return fail(400, { scope, values, errors });
  const result = await createShareLink(api, {
    person_ids: values.person_ids,
    expires_at,
    active: true
  });
  if (!result.ok) {
    if (result.status === 400) {
      return fail(400, { scope, values, errors: { expires_on: result.message } });
    }
    return fail(result.status, { scope, values, message: result.message });
  }
  return { scope, created: { url: `${origin}/shared/${result.data.token}` } };
}
