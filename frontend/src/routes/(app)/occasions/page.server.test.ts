import { describe, expect, it, vi } from 'vitest';

import { actions, load } from './+page.server.ts';

type LoadEvent = Parameters<typeof load>[0];
type ActionEvent = Parameters<typeof actions.create>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const done = { response: new Response(null, { status: 204 }) };

/** Load event; the occasion list reports `total` entries, other lists are empty. */
function loadEvent(query: string, total: number) {
  const GET = vi.fn(async (path: string) =>
    path === '/api/v1/occasions' ? ok({ items: [], total }) : ok({ items: [], total: 0 })
  );
  const event = {
    locals: { api: { GET } },
    url: new URL(`http://localhost/occasions${query}`)
  } as unknown as LoadEvent;
  return { event, GET };
}

const occasionCalls = (GET: ReturnType<typeof vi.fn>) =>
  GET.mock.calls.filter(([path]) => path === '/api/v1/occasions');

describe('load', () => {
  it('reads the requested page', async () => {
    const { event, GET } = loadEvent('?page=2', 450);
    const data = (await load(event)) as { page: number; total: number };
    expect(occasionCalls(GET)[0][1].params.query).toMatchObject({ offset: 200, limit: 200 });
    expect(data).toMatchObject({ page: 2, total: 450 });
  });

  it('redirects beyond the last page and keeps other params', async () => {
    const { event } = loadEvent('?page=5&success=deleted', 450);
    await expect(load(event)).rejects.toMatchObject({
      status: 303,
      location: '/occasions?page=3&success=deleted'
    });
  });

  it('treats an invalid page as page 1', async () => {
    const { event, GET } = loadEvent('?page=abc', 10);
    const data = (await load(event)) as { page: number };
    expect(occasionCalls(GET)[0][1].params.query).toMatchObject({ offset: 0 });
    expect(data.page).toBe(1);
  });

  it('shows the empty state for 0 entries without redirect', async () => {
    const { event } = loadEvent('?page=3', 0);
    const data = (await load(event)) as { occasions: unknown[]; page: number };
    expect(data.occasions).toEqual([]);
  });
});

describe('actions', () => {
  function actionEvent(query: string, fields: Record<string, string>) {
    const body = new FormData();
    for (const [key, value] of Object.entries(fields)) body.set(key, value);
    const api = {
      POST: vi.fn().mockResolvedValue(ok({ id: 'o1' })),
      PUT: vi.fn().mockResolvedValue(ok({ id: 'o1' })),
      DELETE: vi.fn().mockResolvedValue(done)
    };
    return {
      request: { formData: async () => body },
      locals: { api },
      url: new URL(`http://localhost/occasions${query}`)
    } as unknown as ActionEvent;
  }
  const form = { name: 'Fest', date: '2026-05-01', recurrence: 'none', id: 'o1' };

  it('create goes to page 1 even when posted from page 3', async () => {
    await expect(actions.create(actionEvent('?page=3', form))).rejects.toMatchObject({
      status: 303,
      location: '/occasions?success=created'
    });
  });

  it('update stays on the current page', async () => {
    await expect(actions.update(actionEvent('?page=3', form))).rejects.toMatchObject({
      status: 303,
      location: '/occasions?page=3&success=updated'
    });
  });

  it('delete stays on the current page', async () => {
    await expect(actions.delete(actionEvent('?page=3', { id: 'o1' }))).rejects.toMatchObject({
      status: 303,
      location: '/occasions?page=3&success=deleted'
    });
  });
});
