/**
 * Person view (`/persons/<id>`): past gifts and planned giftings side by side, each with its
 * occasion, procurement state and tasks, plus the gift ideas and occasions of the person (F-09).
 * The person itself is edited here as well (F-02).
 *
 * @module routes/(app)/persons/id/+page.server
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
  getPerson,
  getPersonOverview,
  parsePersonForm,
  updatePerson,
  type Result
} from '$lib/server/persons';

/** Returns the data of a successful result; a failure becomes SvelteKit's error page. */
function unwrap<T>(result: Result<T>): T {
  if (!result.ok) error(result.status, result.message);
  return result.data;
}

/**
 * Loads the person and their view in parallel: two requests, the view in a fixed number of
 * queries (QZ-02). An unknown person gives a 404 page.
 */
export const load: PageServerLoad = async ({ locals, params, url }) => {
  const [person, overview] = await Promise.all([
    getPerson(locals.api, params.id),
    getPersonOverview(locals.api, params.id)
  ]);
  // A malformed id (not a UUID) gets 422 from the backend; for the user it is just unknown.
  if (!person.ok && person.status === 422) error(404, 'Person nicht gefunden.');
  return {
    person: unwrap(person),
    overview: unwrap(overview),
    // Only one message exists, so the key is checked instead of shown.
    success: url.searchParams.get('success') === 'updated' ? 'Änderungen gespeichert!' : null
  };
};

/**
 * `update`: validates and saves the person from the URL, then shows this page again with a
 * success message; field errors return with 400 and keep the dialog open.
 */
export const actions: Actions = {
  update: async ({ request, locals, params }) => {
    const { values, errors } = parsePersonForm(await request.formData());
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await updatePerson(locals.api, params.id, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    redirect(303, `/persons/${encodeURIComponent(params.id)}?success=updated`);
  }
};
