/**
 * Logout endpoint (`/logout`), used as a form target only.
 *
 * @module
 */
import { redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

import { SESSION_COOKIE } from '$lib/server/session';

/** There is no logout page; a plain GET goes back to `/`. */
export const load: PageServerLoad = () => {
  redirect(303, '/');
};

/** `default`: revokes the session in the backend, clears the cookie, redirects to `/login`. */
export const actions: Actions = {
  default: async ({ locals, cookies }) => {
    await locals.api.POST('/api/v1/auth/logout');
    cookies.delete(SESSION_COOKIE, { path: '/' });
    redirect(303, '/login');
  }
};
