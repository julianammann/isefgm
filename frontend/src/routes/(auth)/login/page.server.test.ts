import { describe, expect, it, vi } from 'vitest';

import { actions } from './+page.server.ts';

type ActionEvent = Parameters<typeof actions.default>[0];

/** Login form submission whose backend answers with `status`. */
function fakeEvent(status: number) {
  const form = new FormData();
  form.set('email', 'anna@example.org');
  form.set('password', 'correct-horse-battery');
  const request = new Request('http://localhost/login', { method: 'POST', body: form });
  const POST = vi.fn().mockResolvedValue({ response: new Response(null, { status }) });
  return { request, locals: { api: { POST } } } as unknown as ActionEvent;
}

describe('default', () => {
  it.each([
    [401, 'E-Mail-Adresse oder Passwort ist falsch.'],
    [503, 'Gerade laufen zu viele Anmeldungen. Bitte versuche es in ein paar Sekunden erneut.']
  ])('explains a %i in German and keeps the e-mail address', async (status, message) => {
    await expect(actions.default(fakeEvent(status))).resolves.toMatchObject({
      status,
      data: { email: 'anna@example.org', message }
    });
  });
});
