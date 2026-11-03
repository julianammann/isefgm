/**
 * Server-side environment variables, read when the app starts (`$app/env/private`).
 *
 * @module
 */
import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
  API_URL: { schema: (value) => value ?? 'http://localhost:8000' },
  // Optional: unset keeps sign-up closed, see `registrationEnabled`.
  REGISTRATION_ENABLED: { schema: (value) => value }
});
