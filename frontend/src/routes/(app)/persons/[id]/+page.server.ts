/**
 * Person view (`/persons/<id>`): past gifts and planned giftings side by side, each with its
 * occasion, procurement state and tasks, plus the gift ideas and occasions of the person (F-09).
 * The person itself is edited and deleted here as well (F-02).
 *
 * @module routes/(app)/persons/id/+page.server
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
  deletePerson,
  getPerson,
  getPersonOverview,
  parsePersonForm,
  updatePerson
} from '$lib/server/persons';
import { pageCount, pageQuery, parsePage } from '$lib/pagination';
import { unwrap } from '$lib/server/result';

/**
 * Loads the person and their view in parallel: two requests, the view in a fixed number of
 * queries (QZ-02). `?page=` applies to all lists at once, the backend has one offset for them; a
 * page beyond the longest list redirects to its last page. An unknown person gives a 404 page.
 */
export const load: PageServerLoad = async ({ locals, params, url }) => {
  const page = parsePage(url);
  const [person, overviewResult] = await Promise.all([
    getPerson(locals.api, params.id),
    getPersonOverview(locals.api, params.id, page)
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
  return {
    person: unwrap(person),
    overview,
    page,
    total,
    // Only one message exists, so the key is checked instead of shown.
    success: url.searchParams.get('success') === 'updated' ? 'Änderungen gespeichert!' : null
  };
};

/**
 * `update`: validates and saves the person from the URL, then shows this page again with a
 * success message; field errors return with 400 and keep the dialog open. `delete`: removes the
 * person and returns to the list. A failure returns its `scope`, so the page shows the error in
 * the right dialog.
 */
export const actions: Actions = {
  update: async ({ request, locals, params, url }) => {
    const { values, errors } = parsePersonForm(await request.formData());
    if (Object.keys(errors).length) return fail(400, { scope: 'person' as const, values, errors });
    const result = await updatePerson(locals.api, params.id, values);
    if (!result.ok) {
      return fail(result.status, { scope: 'person' as const, values, message: result.message });
    }
    const query = pageQuery(parsePage(url), { success: 'updated' });
    redirect(303, `/persons/${encodeURIComponent(params.id)}${query}`);
  },

  delete: async ({ locals, params }) => {
    const result = await deletePerson(locals.api, params.id);
    if (!result.ok)
      return fail(result.status, { scope: 'delete' as const, message: result.message });
    redirect(303, '/persons?success=deleted');
  }
};
