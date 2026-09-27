/**
 * Shared data for every page that requires a login (route group `(app)`). The guard
 * itself runs in `hooks.server.ts` (`guard` from `$lib/server/guard`), which also
 * covers form actions and page loads; a layout load covers neither. The hook also
 * answers with 503 when the backend cannot tell who is logged in.
 *
 * @module
 */
import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

/** Exposes the logged-in user. */
export const load: LayoutServerLoad = ({ locals }) => {
  // Narrows the type; reaching this without a user means the hook guard is broken.
  if (!locals.user) error(500, 'Route guard did not run');
  return { user: locals.user };
};
