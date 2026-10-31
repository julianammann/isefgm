import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import { createImage, parseImageForm } from './images';

function createApi(handler: (request: Request) => Promise<Response>) {
  const requests: Request[] = [];
  const fetchFn: typeof fetch = (input, init) => {
    const request = input instanceof Request ? input : new Request(input, init);
    requests.push(request);
    return handler(request);
  };

  return { api: createApiClient(fetchFn, 'http://api.test'), requests };
}

const png = () => new File([new Uint8Array(4)], 'a.png', { type: 'image/png' });

describe('createImage', () => {
  it('sends multipart', async () => {
    const { api, requests } = createApi(() =>
      Promise.resolve(
        new Response(JSON.stringify({ id: 'i1' }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    const result = await createImage(api, 'gift1', 'Front', png());
    expect(result.ok).toBe(true);
    expect(requests[0].headers.get('Content-Type')).toMatch(/^multipart\/form-data/);
    const body = await requests[0].formData();
    expect(body.get('gift_id')).toBe('gift1');
    expect(body.get('label')).toBe('Front');
  });

  it('maps 409', async () => {
    const { api } = createApi(() => Promise.resolve(new Response('{}', { status: 409 })));
    expect(await createImage(api, 'gift1', 'Front', png())).toEqual({
      ok: false,
      status: 409,
      message: 'Eine Geschenkidee kann höchstens 5 Bilder haben.'
    });
  });
});

describe('parseImageForm', () => {
  it('requires label and file', () => {
    const { errors } = parseImageForm(new FormData());
    expect(errors).toEqual({
      label: 'Bitte gib eine Bezeichnung an.',
      file: 'Bitte wähle ein Bild aus.'
    });
  });

  it('maps valid values', () => {
    const f = new FormData();
    f.set('label', ' Front ');
    f.set('file', png());
    const { label, file, errors } = parseImageForm(f);
    expect(label).toBe('Front');
    expect(file?.name).toBe('a.png');
    expect(errors).toEqual({});
  });
});
