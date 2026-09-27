/**
 * Registration page (`/register`).
 *
 * @module
 */
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';

import { problemMessage } from '$lib/api/client';
import { forwardSessionCookie } from '$lib/server/session';

/**
 * `default`: creates the account, which logs it in immediately, forwards the session
 * cookie and redirects to `/`.
 */
export const actions: Actions = {
  default: async ({ request, locals, cookies }) => {
    const form = await request.formData();
    const email = String(form.get('email') ?? '');
    const display_name = String(form.get('display_name') ?? '');
    const password = String(form.get('password') ?? '');

    const { data, error, response } = await locals.api.POST('/api/v1/auth/register', {
      body: { email, display_name, password }
    });
    if (!data) {
      const message =
        response.status === 409
          ? 'Diese E-Mail-Adresse ist bereits registriert.'
          : problemMessage(error, 'Registrierung fehlgeschlagen.');
      return fail(response.status >= 400 && response.status < 600 ? response.status : 400, {
        email,
        display_name,
        message
      });
    }

    forwardSessionCookie(response.headers, cookies);
    redirect(303, '/');
  }
};
