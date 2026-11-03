import { describe, expect, it } from 'vitest';

import { berlinDate, endOfBerlinDay } from './expiry';

describe('endOfBerlinDay', () => {
  it('ends a winter day at 23:59:59 CET', () => {
    expect(endOfBerlinDay('2026-12-24')).toBe('2026-12-24T23:59:59+01:00');
  });

  it('ends a summer day at 23:59:59 CEST', () => {
    expect(endOfBerlinDay('2027-07-01')).toBe('2027-07-01T23:59:59+02:00');
  });

  it('uses the evening offset on the days daylight saving switches', () => {
    expect(endOfBerlinDay('2027-03-28')).toBe('2027-03-28T23:59:59+02:00');
    expect(endOfBerlinDay('2026-10-25')).toBe('2026-10-25T23:59:59+01:00');
  });
});

describe('berlinDate', () => {
  it('gives the German calendar day of an instant', () => {
    expect(berlinDate('2026-12-24T22:59:59Z')).toBe('2026-12-24');
    // Already the next day in Berlin, still the 24th in UTC.
    expect(berlinDate('2026-12-24T23:30:00Z')).toBe('2026-12-25');
  });

  it('turns an end of day back into its date', () => {
    expect(berlinDate(endOfBerlinDay('2027-07-01'))).toBe('2027-07-01');
  });
});
