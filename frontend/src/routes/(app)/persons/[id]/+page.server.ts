/**
 * Person view (`/persons/<id>`): past gifts and planned giftings, each with its
 * occasion, procurement state and tasks, plus the gift ideas and occasions of the person (F-09).
 * The person itself is edited and deleted here as well (F-02), and the share links that show
 * their ideas are created and managed here (F-14).
 *
 * @module routes/(app)/persons/id/+page.server
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
  deletePerson,
  getPerson,
  getPersonOverview,
  listPersons,
  parsePersonForm,
  updatePerson
} from '#lib/server/persons.js';
import {
  deleteShareLink,
  getShareLink,
  isOpen,
  listShareLinks,
  parseShareLinkForm,
  shareAction,
  updateShareLink
} from '#lib/server/share-links.js';
import { berlinDate } from '#lib/expiry.js';
import { pageCount, pageQuery, parsePage } from '#lib/pagination.js';
import { unwrap } from '#lib/server/result.js';

/**
 * Display messages for `?success=<key>` after a redirect. Only the key travels in the URL,
 * so the page cannot be made to show arbitrary text and the `Location` header stays ASCII.
 */
const successMessages = {
  updated: 'Änderungen gespeichert!',
  shareUpdated: 'Teilen-Link gespeichert!',
  shareActivated: 'Teilen-Link aktiviert!',
  shareDeactivated: 'Teilen-Link deaktiviert!',
  shareDeleted: 'Teilen-Link gelöscht!'
} as const;

type SuccessKey = keyof typeof successMessages;

function isSuccessKey(key: string | null): key is SuccessKey {
  return key !== null && Object.prototype.hasOwnProperty.call(successMessages, key);
}

/** Redirects back to this page, on the page it was posted from, with the message for `key`. */
function backTo(id: string, url: URL, key: SuccessKey): never {
  redirect(303, `/persons/${encodeURIComponent(id)}${pageQuery(parsePage(url), { success: key })}`);
}

/**
 * Loads the person, their view, their share links and all people for the share dialog in
 * parallel; the view in a fixed number of queries (QZ-02). `?page=` applies to all lists at once,
 * the backend has one offset for them; a page beyond the longest list redirects to its last page.
 * An unknown person gives a 404 page.
 */
export const load: PageServerLoad = async ({ locals, params, url }) => {
  const page = parsePage(url);
  const [person, overviewResult, linksResult, peopleResult] = await Promise.all([
    getPerson(locals.api, params.id),
    getPersonOverview(locals.api, params.id, page),
    listShareLinks(locals.api),
    listPersons(locals.api)
  ]);
  // A malformed id (not a UUID) gets 422 from the backend; for the user it is just unknown.
  if (!person.ok && person.status === 422) error(404, 'Person nicht gefunden.');
  const overview = unwrap(overviewResult);
  const { given, giftings, ideas, occasions } = overview;
  const total = Math.max(given.total, giftings.total, ideas.total, occasions.total);
  const last = pageCount(total);
  if (page > last) {
    const rest = Object.fromEntries([...url.searchParams].filter(([key]) => key !== 'page'));
    redirect(303, `/persons/${encodeURIComponent(params.id)}${pageQuery(last, rest)}`);
  }
  const now = new Date();
  const success = url.searchParams.get('success');
  return {
    person: unwrap(person),
    overview,
    page,
    total,
    // Only the links that show this person; the day is computed here, so it matches the server.
    shareLinks: unwrap(linksResult)
      .filter((link) => link.people.some((p) => p.id === params.id))
      .map((link) => ({
        ...link,
        open: isOpen(link, now),
        expires_on: link.expires_at && berlinDate(link.expires_at),
        created_on: berlinDate(link.created_at)
      })),
    people: unwrap(peopleResult).map(({ id, name }) => ({ id, name })),
    success: isSuccessKey(success) ? successMessages[success] : null,
    // The toast turns red after a delete, so removing a link does not look like saving one.
    deleted: success === 'shareDeleted'
  };
};

/**
 * `update`: validates and saves the person from the URL, then shows this page again with a
 * success message; field errors return with 400 and keep the dialog open. `delete`: removes the
 * person and returns to the list.
 *
 * `share`: creates a share link and returns its URL (see `shareAction`). `updateShare` replaces
 * people and expiry, `toggleShare` deactivates or activates a link, `deleteShare` removes it for good.
 *
 * A failure returns its `scope`, so the page shows the error in the right dialog.
 */
export const actions: Actions = {
  update: async ({ request, locals, params, url }) => {
    const { values, errors } = parsePersonForm(await request.formData());
    if (Object.keys(errors).length) return fail(400, { scope: 'person' as const, values, errors });
    const result = await updatePerson(locals.api, params.id, values);
    if (!result.ok) {
      return fail(result.status, { scope: 'person' as const, values, message: result.message });
    }
    backTo(params.id, url, 'updated');
  },

  delete: async ({ locals, params }) => {
    const result = await deletePerson(locals.api, params.id);
    if (!result.ok)
      return fail(result.status, { scope: 'delete' as const, message: result.message });
    redirect(303, '/persons?success=deleted');
  },

  share: async ({ request, locals, url }) =>
    shareAction(locals.api, await request.formData(), url.origin),

  updateShare: async ({ request, locals, params, url }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const { values, expires_at, errors } = parseShareLinkForm(form);
    const scope = 'shareEdit' as const;
    if (Object.keys(errors).length) return fail(400, { scope, values, errors });
    const result = await updateShareLink(locals.api, id, {
      person_ids: values.person_ids,
      expires_at,
      active: form.get('active') === 'true'
    });
    if (!result.ok) {
      if (result.status === 400) {
        return fail(400, { scope, values, errors: { expires_on: result.message } });
      }
      return fail(result.status, { scope, values, message: result.message });
    }
    backTo(params.id, url, 'shareUpdated');
  },

  toggleShare: async ({ request, locals, params, url }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const active = form.get('active') === 'true';
    const scope = 'shareToggle' as const;
    // Read first: PUT replaces everything, and only the flag should change.
    const current = await getShareLink(locals.api, id);
    if (!current.ok) return fail(current.status, { scope, message: current.message });
    const result = await updateShareLink(locals.api, id, {
      person_ids: current.data.people.map((p) => p.id),
      expires_at: current.data.expires_at,
      active
    });
    if (!result.ok) return fail(result.status, { scope, message: result.message });
    backTo(params.id, url, active ? 'shareActivated' : 'shareDeactivated');
  },

  deleteShare: async ({ request, locals, params, url }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteShareLink(locals.api, id);
    if (!result.ok) {
      return fail(result.status, { scope: 'shareDelete' as const, message: result.message });
    }
    backTo(params.id, url, 'shareDeleted');
  }
};
