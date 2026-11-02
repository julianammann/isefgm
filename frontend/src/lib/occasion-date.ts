/**
 * Date text of an occasion in lists and forms.
 *
 * @module
 */
import type { components } from '$lib/api/schema';

type Occasion = components['schemas']['OccasionOut'];

/**
 * Date text of an occasion: the rule's date for rule occasions, the stored date otherwise.
 * `birthday` is the person's birthday on that person's page; Geburtstag then shows its day.
 */
export function occasionDateLabel(
  occasion: Pick<Occasion, 'date' | 'rule'>,
  birthday?: string | null
): string {
  const date = occasion.rule === 'birthday' ? birthday : occasion.date;
  if (!date) return 'Datum je Person';
  const [year, month, day] = date.split('-');
  // Christmas is always 24.12. and a birthday recurs on its day, so the year adds nothing.
  return occasion.rule === 'christmas' || occasion.rule === 'birthday'
    ? `${day}.${month}.`
    : `${day}.${month}.${year}`;
}
