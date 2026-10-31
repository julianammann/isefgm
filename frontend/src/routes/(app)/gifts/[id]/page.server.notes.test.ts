import { describe, expect, it, vi } from 'vitest';

import { actions } from './+page.server.ts';

type ActionEvent = Parameters<typeof actions.createNote>[0];

const status = (code: number) => ({ response: new Response(null, { status: code }) });

/** Action event with the given backend mocks and form fields. */
function event(api: Record<string, unknown>, fields: Record<string, string>) {
  const body = new FormData();
  for (const [k, v] of Object.entries(fields)) body.set(k, v);
  return {
    request: new Request('http://localhost/gifts/g1', { method: 'POST', body }),
    locals: { api },
    params: { id: 'g1' }
  } as unknown as ActionEvent;
}

describe('createNote', () => {
  it('keeps the input and reports errors in the note scope', async () => {
    const POST = vi.fn();
    await expect(actions.createNote(event({ POST }, { label: '', text: 'M' }))).resolves.toEqual(
      expect.objectContaining({
        status: 400,
        data: {
          scope: 'note',
          values: { gift_id: 'g1', label: '', text: 'M' },
          errors: { label: 'Bitte gib eine Bezeichnung an.' }
        }
      })
    );
    expect(POST).not.toHaveBeenCalled();
  });

  it('redirects back with the success key', async () => {
    const POST = vi.fn().mockResolvedValue({
      data: { id: 'n1' },
      response: new Response(null, { status: 201 })
    });
    await expect(
      actions.createNote(event({ POST }, { label: 'L', text: 'M' }))
    ).rejects.toMatchObject({ status: 303, location: '/gifts/g1?success=noteCreated' });
  });
});

describe('updateNote', () => {
  it('sends the note id from the form and reports a backend failure in the note scope', async () => {
    const PUT = vi.fn().mockResolvedValue(status(404));
    await expect(
      actions.updateNote(event({ PUT }, { id: 'n1', label: 'L', text: 'M' }))
    ).resolves.toMatchObject({
      status: 404,
      data: { scope: 'note', message: 'Notiz nicht gefunden.' }
    });
    expect(PUT.mock.calls[0][1].params.path.note_id).toBe('n1');
  });
});

describe('deleteNote', () => {
  it('redirects back after deleting', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(204));
    await expect(actions.deleteNote(event({ DELETE }, { id: 'n1' }))).rejects.toMatchObject({
      location: '/gifts/g1?success=noteDeleted'
    });
  });

  it('reports a failure in the delete scope', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(404));
    await expect(actions.deleteNote(event({ DELETE }, { id: 'n1' }))).resolves.toMatchObject({
      status: 404,
      data: { scope: 'delete' }
    });
  });
});

describe('createLink', () => {
  it('rejects a non-http address in the link scope', async () => {
    const POST = vi.fn();
    await expect(
      actions.createLink(event({ POST }, { label: 'L', url: 'ftp://x' }))
    ).resolves.toMatchObject({
      status: 400,
      data: { scope: 'link', errors: { url: expect.any(String) } }
    });
    expect(POST).not.toHaveBeenCalled();
  });

  it('redirects back with the success key', async () => {
    const POST = vi.fn().mockResolvedValue({
      data: { id: 'l1' },
      response: new Response(null, { status: 201 })
    });
    await expect(
      actions.createLink(event({ POST }, { label: 'L', url: 'https://example.com' }))
    ).rejects.toMatchObject({ location: '/gifts/g1?success=linkCreated' });
  });
});

describe('updateLink and deleteLink', () => {
  it('update redirects with linkUpdated', async () => {
    const PUT = vi.fn().mockResolvedValue({
      data: { id: 'l1' },
      response: new Response(null, { status: 200 })
    });
    await expect(
      actions.updateLink(event({ PUT }, { id: 'l1', label: 'L', url: 'https://example.com' }))
    ).rejects.toMatchObject({ location: '/gifts/g1?success=linkUpdated' });
    expect(PUT.mock.calls[0][1].params.path.link_id).toBe('l1');
  });

  it('delete redirects with linkDeleted', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(204));
    await expect(actions.deleteLink(event({ DELETE }, { id: 'l1' }))).rejects.toMatchObject({
      location: '/gifts/g1?success=linkDeleted'
    });
  });
});
