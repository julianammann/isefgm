import type { components } from '$lib/api/schema';

type Occasion = components['schemas']['OccasionOut'];

/** Date text of an occasion: the rule's date for rule occasions, the stored date otherwise. */
export function occasionDateLabel(occasion: Pick<Occasion, 'date' | 'rule'>): string {
  if (occasion.rule === 'birthday' || !occasion.date) return 'Datum je Person';
  const [year, month, day] = occasion.date.split('-');
  // Christmas is always 24.12., so the year adds nothing.
  return occasion.rule === 'christmas' ? `${day}.${month}.` : `${day}.${month}.${year}`;
}
