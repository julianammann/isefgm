/**
 * Data for login and registration: whether the sign-up link and form are shown.
 *
 * @module
 */
import { REGISTRATION_ENABLED } from '$app/env/private';
import type { LayoutServerLoad } from './$types';

import { registrationEnabled } from '#lib/server/registration.js';

/** Reads `REGISTRATION_ENABLED`, the same variable the backend enforces. */
export const load: LayoutServerLoad = () => ({
  registrationEnabled: registrationEnabled(REGISTRATION_ENABLED)
});
