/**
 * Backend and database status for the indicator in the page header.
 *
 * @module
 */
import type { Health } from '$lib/api/client';

/** Traffic-light level of the status indicator. */
export type StatusLevel = 'ok' | 'degraded' | 'down';

/** What the header shows: a colour level plus a text for tooltip and screen readers. */
export interface SystemStatus {
  level: StatusLevel;
  label: string;
}

/**
 * Maps the readiness response to the indicator. `null` means the backend did not
 * answer; `degraded` means it answered but the database did not.
 */
export function systemStatus(health: Health | null): SystemStatus {
  if (!health) return { level: 'down', label: 'Backend nicht erreichbar' };
  if (health.status === 'ok' && health.database) {
    return { level: 'ok', label: 'Backend und Datenbank erreichbar' };
  }
  return { level: 'degraded', label: 'Backend erreichbar, Datenbank nicht erreichbar' };
}
