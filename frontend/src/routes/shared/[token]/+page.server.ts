/**
 * Shared view (`/shared/<token>`): the gift ideas of the people behind a share link, read-only and
 * without a login (F-14). Outside the `(app)` and `(auth)` groups, so the route guard lets
 * everyone through; `hooks.server.ts` keeps the token out of referrers, caches and search engines.
 *
 * @module routes/shared/token/+page.server
 */
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

import { berlinDate } from '#lib/expiry.js';
import { getSharedList } from '#lib/server/share-links.js';

/** Message for every link that does not open; the reason (unknown, deactivated, expired) stays hidden. */
const NOT_VALID = 'Dieser Link ist nicht gültig oder nicht mehr aktiv.';

/**
 * Loads what the link shows. Any token the backend does not open, including a malformed one (422),
 * gives the same 404 page.
 */
export const load: PageServerLoad = async ({ locals, params }) => {
  const result = await getSharedList(locals.api, params.token);
  if (!result.ok) {
    if (result.status === 404 || result.status === 422) error(404, NOT_VALID);
    error(result.status, result.message);
  }
  return {
    shared: result.data,
    // The day in German time, computed here so server and browser show the same date.
    expires_on: result.data.expires_at && berlinDate(result.data.expires_at)
  };
};
