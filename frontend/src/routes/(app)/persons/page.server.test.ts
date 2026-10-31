import { describe, expect, it, vi } from 'vitest';

import { actions, load } from './+page.server.ts';

type LoadEvent = Parameters<typeof load>[0];
type ActionEvent = Parameters<typeof actions.update>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const noContent = () => ({ response: new Response(null, { status: 204 }) });

function loadEvent(search: string, total: number, items: unknown[] = []) {
  const GET = vi.fn(async () => ok({ items, total }));
  const event = {
    locals: { api: { GET } },
    url: new URL(`http://localhost/persons${search}`)
  } as unknown as LoadEvent;
  return { event, GET };
}

function actionEvent(search: string, api: object, fields: Record<string, string>) {
  const request = new Request('http://localhost/persons', {
    method: 'POST',
    body: new URLSearchParams(fields)
  });
  return {
    request,
    locals: { api },
    url: new URL(`http://localhost/persons${search}`)
  } as unknown as ActionEvent;
}

const redirectTo = (location: string) => ({ status: 303, location });

describe('load', () => {
  it('requests the page from the backend and returns page and total', async () => {
    const { event, GET } = loadEvent('?page=2', 450, [{ id: 'p1' }]);
    const data = (await load(event)) as { page: number; total: number };
    expect(GET).toHaveBeenCalledWith('/api/v1/people', {
      params: { query: { limit: 200, offset: 200 } }
    });
    expect(data).toMatchObject({ page: 2, total: 450 });
  });

  it('redirects beyond the last page and keeps other params', async () => {
    const { event } = loadEvent('?page=5&success=deleted', 450);
    await expect(load(event)).rejects.toMatchObject(redirectTo('/persons?page=3&success=deleted'));
  });

  it('treats an invalid page as page 1', async () => {
    const { event, GET } = loadEvent('?page=abc', 10);
    await load(event);
    expect(GET).toHaveBeenCalledWith('/api/v1/people', {
      params: { query: { limit: 200, offset: 0 } }
    });
  });

  it('shows the empty state without redirect for total 0', async () => {
    const { event } = loadEvent('?page=3', 0);
    await expect(load(event)).resolves.toMatchObject({ persons: [], total: 0 });
  });

  it('finds the person to edit among the page items', async () => {
    const { event } = loadEvent('?edit=p1', 1, [{ id: 'p1' }]);
    await expect(load(event)).resolves.toMatchObject({ editing: { id: 'p1' } });
  });
});

describe('actions', () => {
  it('create goes to page 1 even when posted from page 3', async () => {
    const POST = vi.fn().mockResolvedValue(ok({ id: 'p1' }));
    const event = actionEvent('?page=3&/create', { POST }, { name: 'A' });
    await expect(actions.create(event)).rejects.toMatchObject(
      redirectTo('/persons?success=created')
    );
  });

  it('update stays on the posted page', async () => {
    const PUT = vi.fn().mockResolvedValue(ok({ id: 'p1' }));
    const event = actionEvent('?page=3&/update', { PUT }, { id: 'p1', name: 'A' });
    await expect(actions.update(event)).rejects.toMatchObject(
      redirectTo('/persons?page=3&success=updated')
    );
  });

  it('delete stays on the posted page', async () => {
    const DELETE = vi.fn().mockResolvedValue(noContent());
    const event = actionEvent('?page=3&/delete', { DELETE }, { id: 'p1' });
    await expect(actions.delete(event)).rejects.toMatchObject(
      redirectTo('/persons?page=3&success=deleted')
    );
  });
});
