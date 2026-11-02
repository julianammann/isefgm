import { describe, expect, it } from 'vitest';

import { formatPriceRange, giftingSummary, type GiftingStatus } from './display';

describe('formatPriceRange', () => {
  const gift = (price_from: string | null, price_to: string | null, currency: string | null) => ({
    price_from,
    price_to,
    currency
  });
  it('shows both ends with the currency', () => {
    expect(formatPriceRange(gift('20.00', '30.50', 'EUR'))).toBe('20,00 – 30,50 EUR');
  });
  it('shows an open range from below or above', () => {
    expect(formatPriceRange(gift('20.00', null, 'EUR'))).toBe('ab 20,00 EUR');
    expect(formatPriceRange(gift(null, '30.00', null))).toBe('bis 30,00');
  });
  it('is empty without a price, even with a currency', () => {
    expect(formatPriceRange(gift(null, null, 'EUR'))).toBe('');
  });
});

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
