/**
 * Data for login and registration: whether the sign-up link and form are shown.
 *
 * @module
 */
import { env } from '$env/dynamic/private';
import type { LayoutServerLoad } from './$types';

import { registrationEnabled } from '$lib/server/registration';

/** Reads `REGISTRATION_ENABLED`, the same variable the backend enforces. */
export const load: LayoutServerLoad = () => ({
  registrationEnabled: registrationEnabled(env.REGISTRATION_ENABLED)
});
