/**
 * Data for every page: the backend and database status behind the indicator dot.
 *
 * @module
 */
import type { LayoutServerLoad } from './$types';

import { systemStatus } from '$lib/health';

/** Loads `GET /api/v1/health/ready`; an unreachable backend becomes a red dot, not an error. */
export const load: LayoutServerLoad = async ({ locals }) => {
  let health = null;
  try {
    ({ data: health = null } = await locals.api.GET('/api/v1/health/ready'));
  } catch {
    // Backend unreachable: systemStatus(null) reports it.
  }
  return { status: systemStatus(health) };
};
