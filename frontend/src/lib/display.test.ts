import { describe, expect, it } from 'vitest';

import { giftingSummary } from './display';

describe('giftingSummary', () => {
  it('says so when there is no gifting yet', () => {
    expect(giftingSummary([])).toBe('Noch keine Beschenkung');
  });

  it('shows a single gifting in the singular', () => {
    expect(giftingSummary(['idea'])).toBe('1 Beschenkung: ○ Idee');
  });

  it('counts repeated statuses and keeps the status order', () => {
    expect(giftingSummary(['given', 'planned', 'planned'])).toBe(
      '3 Beschenkungen: 2× ◔ Geplant · ✓ Verschenkt'
    );
  });
});
