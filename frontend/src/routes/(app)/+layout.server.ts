/**
 * Shared data for every page that requires a login (route group `(app)`). The guard
 * itself runs in `hooks.server.ts` (`guard` from `$lib/server/guard`), which also
 * covers form actions and page loads; a layout load covers neither.
 *
 * @module
 */
import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

import { SERVICE_UNAVAILABLE } from '$lib/server/guard';

/** Exposes the logged-in user; renders the 503 page if the backend could not tell. */
export const load: LayoutServerLoad = ({ locals }) => {
  if (locals.authUnavailable) error(503, SERVICE_UNAVAILABLE);
  // Narrows the type; reaching this without a user means the hook guard is broken.
  if (!locals.user) error(500, 'Route guard did not run');
  return { user: locals.user };
};
