import { describe, expect, it } from 'vitest';

import { giftingSummary, type GiftingStatus } from './display';

/** The line as the list shows it. */
function text(statuses: GiftingStatus[]) {
  const { lead, parts } = giftingSummary(statuses);
  return lead + parts.map((p) => `${p.count}${p.icon} ${p.label}`).join(' · ');
}

describe('giftingSummary', () => {
  it('says so when there is no gifting yet', () => {
    expect(text([])).toBe('Noch keine Beschenkung');
  });

  it('shows a single gifting in the singular', () => {
    expect(text(['idea'])).toBe('1 Beschenkung: ○ Idee');
  });

  it('counts repeated statuses and keeps the status order', () => {
    expect(text(['given', 'planned', 'planned'])).toBe(
      '3 Beschenkungen: 2× ◔ Geplant · ✓ Verschenkt'
    );
  });

  it('keeps the icon apart from the text read aloud', () => {
    expect(giftingSummary(['planned', 'planned']).parts).toEqual([
      { count: '2× ', icon: '◔', label: 'Geplant' }
    ]);
  });
});
