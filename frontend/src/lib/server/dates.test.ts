import { describe, expect, it } from 'vitest';

import { isValidDate } from './dates';

describe('isValidDate', () => {
  it.each(['2026-02-28', '2028-02-29', '0001-01-01', '9999-12-31'])('accepts %s', (value) => {
    expect(isValidDate(value)).toBe(true);
  });

  it.each([
    '2026-02-30',
    '2026-02-29',
    '2026-13-01',
    '2026-00-10',
    '0000-01-01',
    '12/24/2026',
    '1',
    '2026-2-3',
    '2026-02-28T10:00:00Z',
    ''
  ])('rejects %j', (value) => {
    expect(isValidDate(value)).toBe(false);
  });
});
