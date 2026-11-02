/**
 * Date checks for form input.
 *
 * @module
 */

/** True for a `YYYY-MM-DD` string naming a real calendar date the backend can store (year 1+). */
export function isValidDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const [year, month, day] = match.slice(1).map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return year > 0 && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}
