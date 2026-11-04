/**
 * Expiry dates of share links: the user picks a day, the backend stores an instant.
 * Browser-safe, no server imports.
 *
 * @module
 */

/** Calendar of the users; the backend evaluates calendar dates in the same zone. */
const TIME_ZONE = 'Europe/Berlin';

/** The calendar day (`YYYY-MM-DD`) of an instant in German time. */
export function berlinDate(instant: Date | string): string {
  // sv-SE writes dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(new Date(instant));
}

/**
 * The last second of a calendar day in German time, e.g. `2026-12-24T23:59:59+01:00`, so a link
 * "valid until 24.12." still opens on the evening of that day.
 */
export function endOfBerlinDay(date: string): string {
  const [year, month, day] = date.split('-').map(Number);
  // Noon of the same day: daylight saving switches at night, so the offset is the evening one.
  const noon = new Date(Date.UTC(year, month - 1, day, 12));
  const zone = new Intl.DateTimeFormat('en-US', { timeZone: TIME_ZONE, timeZoneName: 'longOffset' })
    .formatToParts(noon)
    .find((part) => part.type === 'timeZoneName')?.value;
  const offset = zone?.replace('GMT', '') || 'Z';
  return `${date}T23:59:59${offset}`;
}
