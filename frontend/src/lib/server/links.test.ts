import { describe, expect, it } from 'vitest';

import { isHttpUrl, parseLinkForm } from './links';

describe('isHttpUrl', () => {
  it('accepts only absolute http and https addresses', () => {
    expect(isHttpUrl('https://example.org/x')).toBe(true);
    expect(isHttpUrl('javascript:alert(1)')).toBe(false);
    expect(isHttpUrl('example.org')).toBe(false);
    expect(isHttpUrl('ftp://example.org')).toBe(false);
  });
});

describe('parseLinkForm', () => {
  it('rejects a relative address', () => {
    const f = new FormData();
    f.set('label', 'Shop');
    f.set('url', 'example.org');
    expect(parseLinkForm(f, 'gift1').errors.url).toBe(
      'Bitte gib eine vollständige Adresse mit http:// oder https:// an.'
    );
  });

  it('requires label and address and limits the address length', () => {
    const empty = parseLinkForm(new FormData(), 'gift1').errors;
    expect(empty.label).toBe('Bitte gib eine Bezeichnung an.');
    expect(empty.url).toBe('Bitte gib eine Adresse an.');
    const f = new FormData();
    f.set('label', 'Shop');
    f.set('url', 'https://example.org/' + 'x'.repeat(2048));
    expect(parseLinkForm(f, 'gift1').errors.url).toBe(
      'Die Adresse darf höchstens 2048 Zeichen lang sein.'
    );
  });

  it('maps valid values', () => {
    const f = new FormData();
    f.set('label', 'Shop');
    f.set('url', ' https://example.org/x ');
    expect(parseLinkForm(f, 'gift1')).toEqual({
      values: { gift_id: 'gift1', label: 'Shop', url: 'https://example.org/x' },
      errors: {}
    });
  });
});
