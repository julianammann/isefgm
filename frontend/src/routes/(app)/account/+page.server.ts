/**
 * Account page (`/account`): delete the account (F-17).
 *
 * @module
 */
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';

import { problemMessage } from '$lib/api/client';
import { SESSION_COOKIE } from '$lib/server/session';

/**
 * `delete`: requires the `confirm` checkbox, deletes the account in the backend, clears
 * the session cookie and redirects to `/login`.
 */
export const actions: Actions = {
  delete: async ({ request, locals, cookies }) => {
    const form = await request.formData();
    if (form.get('confirm') !== 'on') {
      return fail(400, { message: 'Bitte bestätige die Löschung.' });
    }
    const { error, response } = await locals.api.DELETE('/api/v1/auth/account');
    if (!response.ok) {
      return fail(response.status, { message: problemMessage(error, 'Löschen fehlgeschlagen.') });
    }
    cookies.delete(SESSION_COOKIE, { path: '/' });
    redirect(303, '/login');
  }
};
