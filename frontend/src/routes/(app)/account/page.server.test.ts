import { describe, expect, it, vi } from 'vitest';

import { actions } from './+page.server.ts';

type ActionEvent = Parameters<typeof actions.logoutAll>[0];

/** Action event whose backend answers every POST with `status`. */
function fakeEvent(status: number) {
  const POST = vi.fn().mockResolvedValue({ response: new Response(null, { status }) });
  const cookies = {
    get: vi.fn((name: string) => (name === '__Host-session' ? 'token' : undefined)),
    delete: vi.fn()
  };
  const event = { locals: { api: { POST } }, cookies } as unknown as ActionEvent;
  return { event, POST, cookies };
}

describe('logoutAll', () => {
  it('ends every session, clears the cookie and redirects to the login', async () => {
    const { event, POST, cookies } = fakeEvent(204);
    await expect(actions.logoutAll(event)).rejects.toMatchObject({
      status: 303,
      location: '/login'
    });
    expect(POST).toHaveBeenCalledWith('/api/v1/auth/logout-all');
    expect(cookies.delete).toHaveBeenCalledExactlyOnceWith('__Host-session', {
      path: '/',
      secure: true
    });
  });

  it('keeps the cookie and reports a backend failure', async () => {
    const { event, cookies } = fakeEvent(503);
    await expect(actions.logoutAll(event)).resolves.toMatchObject({
      status: 503,
      data: { logoutAllMessage: 'Abmelden auf allen Geräten fehlgeschlagen.' }
    });
    expect(cookies.delete).not.toHaveBeenCalled();
  });
});
