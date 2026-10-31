import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import { deleteNote, listNotes, parseNoteForm } from './notes';

function createApi(handler: (request: Request) => Promise<Response>) {
  const requests: Request[] = [];
  const fetchFn: typeof fetch = (input, init) => {
    const request = input instanceof Request ? input : new Request(input, init);
    requests.push(request);
    return handler(request);
  };

  return { api: createApiClient(fetchFn, 'http://api.test'), requests };
}

describe('listNotes', () => {
  it('filters by gift', async () => {
    const { api, requests } = createApi(() =>
      Promise.resolve(
        new Response(JSON.stringify({ items: [], total: 0 }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    const result = await listNotes(api, 'gift1');
    expect(result).toEqual({ ok: true, data: [] });
    expect(requests[0].url).toContain('gift_id=gift1');
    expect(requests[0].url).toContain('limit=200');
  });
});

describe('parseNoteForm', () => {
  it('requires label and text', () => {
    const { errors } = parseNoteForm(new FormData(), 'gift1');
    expect(errors.label).toBe('Bitte gib eine Bezeichnung an.');
    expect(errors.text).toBe('Bitte gib einen Text an.');
  });

  it('rejects a 101-character label', () => {
    const f = new FormData();
    f.set('label', 'x'.repeat(101));
    f.set('text', 'ok');
    const { errors } = parseNoteForm(f, 'gift1');
    expect(errors.label).toBe('Die Bezeichnung darf höchstens 100 Zeichen lang sein.');
    expect(errors.text).toBeUndefined();
  });

  it('rejects a 2001-character text and maps valid values', () => {
    const f = new FormData();
    f.set('label', ' Größe ');
    f.set('text', 'x'.repeat(2001));
    expect(parseNoteForm(f, 'gift1').errors.text).toBe(
      'Der Text darf höchstens 2000 Zeichen lang sein.'
    );
    f.set('text', 'M');
    expect(parseNoteForm(f, 'gift1')).toEqual({
      values: { gift_id: 'gift1', label: 'Größe', text: 'M' },
      errors: {}
    });
  });
});

describe('deleteNote', () => {
  it('maps 404', async () => {
    const { api } = createApi(() => Promise.resolve(new Response(null, { status: 404 })));
    expect(await deleteNote(api, 'n1')).toEqual({
      ok: false,
      status: 404,
      message: 'Notiz nicht gefunden.'
    });
  });
});
