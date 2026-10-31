import { describe, expect, it, vi } from 'vitest';

import { MAX_IMAGE_BYTES } from '$lib/images';
import { actions } from './+page.server.ts';

type ActionEvent = Parameters<typeof actions.delete>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const status = (code: number) => ({ response: new Response(null, { status: code }) });

/** Action event with the given backend methods and form fields. */
function event(api: Record<string, unknown>, fields: Record<string, string | Blob> = {}) {
  const body = new FormData();
  for (const [key, value] of Object.entries(fields)) body.set(key, value);
  return {
    request: { formData: async () => body },
    locals: { api },
    params: { id: 'g1' }
  } as unknown as ActionEvent;
}

const png = (size = 10) => new File([new Uint8Array(size)], 'a.png', { type: 'image/png' });

describe('createImage', () => {
  it('rejects an oversized file before calling the backend', async () => {
    const POST = vi.fn();
    const result = await actions.createImage(
      event({ POST }, { label: 'Laden', file: png(MAX_IMAGE_BYTES + 1) })
    );
    expect(result).toMatchObject({
      status: 400,
      data: {
        scope: 'image',
        values: { label: 'Laden' },
        errors: { file: 'Das Bild ist zu groß. Erlaubt sind höchstens 5 MB.' }
      }
    });
    expect(POST).not.toHaveBeenCalled();
  });

  it('reports a backend failure in the image dialog', async () => {
    const POST = vi.fn().mockResolvedValue(status(409));
    await expect(
      actions.createImage(event({ POST }, { label: 'Laden', file: png() }))
    ).resolves.toMatchObject({
      status: 409,
      data: { scope: 'image', values: { label: 'Laden' } }
    });
  });

  it('uploads and redirects with the success key', async () => {
    const POST = vi.fn().mockResolvedValue(ok({ id: 'i1' }));
    await expect(
      actions.createImage(event({ POST }, { label: 'Laden', file: png() }))
    ).rejects.toMatchObject({ status: 303, location: '/gifts/g1?success=imageCreated' });
  });
});

describe('updateImage', () => {
  it('rejects an empty label before calling the backend', async () => {
    const PUT = vi.fn();
    await expect(
      actions.updateImage(event({ PUT }, { id: 'i1', label: ' ' }))
    ).resolves.toMatchObject({
      status: 400,
      data: { scope: 'image', errors: { label: expect.any(String) } }
    });
    expect(PUT).not.toHaveBeenCalled();
  });

  it('saves the label and redirects', async () => {
    const PUT = vi.fn().mockResolvedValue(ok({ id: 'i1' }));
    await expect(
      actions.updateImage(event({ PUT }, { id: 'i1', label: 'Neu' }))
    ).rejects.toMatchObject({ status: 303, location: '/gifts/g1?success=imageUpdated' });
    expect(PUT.mock.calls[0][1]).toMatchObject({
      params: { path: { image_id: 'i1' } },
      body: { label: 'Neu' }
    });
  });
});

describe('deleteImage', () => {
  it('reports a failure in the delete scope', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(404));
    await expect(actions.deleteImage(event({ DELETE }, { id: 'i1' }))).resolves.toMatchObject({
      status: 404,
      data: { scope: 'delete' }
    });
  });

  it('deletes and redirects', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(204));
    await expect(actions.deleteImage(event({ DELETE }, { id: 'i1' }))).rejects.toMatchObject({
      status: 303,
      location: '/gifts/g1?success=imageDeleted'
    });
  });
});
