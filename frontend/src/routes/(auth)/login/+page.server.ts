/**
 * Login page (`/login`).
 *
 * @module
 */
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';

import { problemMessage } from '$lib/api/client';
import { forwardSessionCookie, safeNext } from '$lib/server/session';

/**
 * `default`: logs in with e-mail and password, forwards the session cookie and redirects
 * to the `next` query parameter (same-origin paths only) or `/`.
 */
export const actions: Actions = {
  default: async ({ request, locals, cookies, url }) => {
    const form = await request.formData();
    const email = String(form.get('email') ?? '');
    const password = String(form.get('password') ?? '');

    const { data, error, response } = await locals.api.POST('/api/v1/auth/login', {
      body: { email, password }
    });
    if (!data) {
      const message =
        response.status === 401
          ? 'E-Mail-Adresse oder Passwort ist falsch.'
          : problemMessage(error, 'Anmeldung fehlgeschlagen.');
      return fail(response.status >= 400 && response.status < 600 ? response.status : 400, {
        email,
        message
      });
    }

    forwardSessionCookie(response.headers, cookies);
    redirect(303, safeNext(url.searchParams.get('next')));
  }
};
