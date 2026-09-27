import { describe, expect, it, vi } from 'vitest';

import { actions } from './+page.server.ts';

type ActionEvent = Parameters<typeof actions.default>[0];

/** Registration form submission whose backend answers with `status`. */
function fakeEvent(status: number) {
  const form = new FormData();
  form.set('email', 'anna@example.org');
  form.set('display_name', 'Anna');
  form.set('password', 'correct-horse-battery');
  const request = new Request('http://localhost/register', { method: 'POST', body: form });
  const POST = vi.fn().mockResolvedValue({ response: new Response(null, { status }) });
  return { request, locals: { api: { POST } } } as unknown as ActionEvent;
}

describe('default', () => {
  it.each([
    [409, 'Diese E-Mail-Adresse ist bereits registriert.'],
    [503, 'Gerade laufen zu viele Registrierungen. Bitte versuche es in ein paar Sekunden erneut.']
  ])('explains a %i in German and keeps the form values', async (status, message) => {
    await expect(actions.default(fakeEvent(status))).resolves.toMatchObject({
      status,
      data: { email: 'anna@example.org', display_name: 'Anna', message }
    });
  });
});
