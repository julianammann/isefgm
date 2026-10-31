import { describe, expect, it } from 'vitest';

import { failure, listAll } from './result';

function page(items: string[], total: number) {
  return { data: { items, total }, response: new Response(null, { status: 200 }) };
}

describe('listAll', () => {
  it('reads every page', async () => {
    const offsets: number[] = [];
    const pages = [page(['a', 'b'], 3), page(['c'], 3)];
    const result = await listAll((offset) => {
      offsets.push(offset);
      return Promise.resolve(pages[offsets.length - 1]);
    }, {});
    expect(result).toEqual({ ok: true, data: ['a', 'b', 'c'] });
    expect(offsets).toEqual([0, 2]);
  });
});

describe('failure', () => {
  it('falls back to the shared texts', () => {
    expect(failure(401, {}).message).toBe('Sitzung abgelaufen. Bitte erneut anmelden.');
    expect(failure(418, {}).message).toBe('Unerwarteter Fehler. Bitte später erneut versuchen.');
  });

  it('prefers the given texts', () => {
    expect(failure(404, { 404: 'Weg.' }).message).toBe('Weg.');
  });
});
