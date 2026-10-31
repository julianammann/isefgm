import { describe, expect, it, vi } from 'vitest';

import { actions } from './+page.server.ts';

type ActionEvent = Parameters<typeof actions.createTask>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const status = (code: number) => ({ response: new Response(null, { status: code }) });

function event(fields: Record<string, string>, api: object) {
  const body = new FormData();
  for (const [k, v] of Object.entries(fields)) body.set(k, v);
  return {
    request: { formData: async () => body },
    locals: { api },
    params: { id: 'g1' }
  } as unknown as ActionEvent;
}

const redirectTo = (url: string) => ({ status: 303, location: url });

describe('createTask', () => {
  it('creates the task on the posted gifting and redirects', async () => {
    const POST = vi.fn().mockResolvedValue(ok({ id: 't1' }));
    await expect(
      actions.createTask(event({ gifting_id: 'f1', title: 'Wrap', status: 'open' }, { POST }))
    ).rejects.toMatchObject(redirectTo('/gifts/g1?success=taskCreated'));
    expect(POST).toHaveBeenCalledWith('/api/v1/tasks', {
      body: { title: 'Wrap', status: 'open', due_on: null, gifting_id: 'f1' }
    });
  });

  it('fails with 400 in the task scope for a missing title', async () => {
    const POST = vi.fn();
    await expect(
      actions.createTask(event({ gifting_id: 'f1', title: '' }, { POST }))
    ).resolves.toMatchObject({
      status: 400,
      data: { scope: 'task', errors: { title: expect.any(String) } }
    });
    expect(POST).not.toHaveBeenCalled();
  });
});

describe('updateTask', () => {
  it('replaces the task and redirects', async () => {
    const PUT = vi.fn().mockResolvedValue(ok({ id: 't1' }));
    await expect(
      actions.updateTask(
        event(
          { id: 't1', gifting_id: 'f1', title: 'Wrap', status: 'done', due_on: '2026-12-01' },
          { PUT }
        )
      )
    ).rejects.toMatchObject(redirectTo('/gifts/g1?success=taskUpdated'));
    expect(PUT).toHaveBeenCalledWith('/api/v1/tasks/{task_id}', {
      params: { path: { task_id: 't1' } },
      body: { title: 'Wrap', status: 'done', due_on: '2026-12-01', gifting_id: 'f1' }
    });
  });
});

describe('deleteTask', () => {
  it('deletes the task and redirects', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(204));
    await expect(actions.deleteTask(event({ id: 't1' }, { DELETE }))).rejects.toMatchObject(
      redirectTo('/gifts/g1?success=taskDeleted')
    );
  });

  it('reports a failure in the delete scope', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(404));
    await expect(actions.deleteTask(event({ id: 't1' }, { DELETE }))).resolves.toMatchObject({
      status: 404,
      data: { scope: 'delete' }
    });
  });
});

describe('createTaskForGift', () => {
  it("uses the idea's people", async () => {
    const GET = vi
      .fn()
      .mockResolvedValue(ok({ id: 'g1', title: 'Buch', people: [{ id: 'p1', name: 'X' }] }));
    const POST = vi.fn(async (path: string) =>
      ok(path === '/api/v1/giftings' ? { id: 'f9' } : { id: 't1' })
    );
    await expect(
      actions.createTaskForGift(event({ title: 'Wrap' }, { GET, POST }))
    ).rejects.toMatchObject(redirectTo('/gifts/g1?success=taskCreated'));
    expect(POST).toHaveBeenNthCalledWith(
      1,
      '/api/v1/giftings',
      expect.objectContaining({
        body: expect.objectContaining({ person_ids: ['p1'], gift_id: 'g1' })
      })
    );
    expect(POST).toHaveBeenNthCalledWith(
      2,
      '/api/v1/tasks',
      expect.objectContaining({
        body: expect.objectContaining({ gifting_id: 'f9', title: 'Wrap' })
      })
    );
  });
});
