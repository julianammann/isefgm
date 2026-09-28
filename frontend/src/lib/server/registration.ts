/**
 * Whether sign-up is open, read from `REGISTRATION_ENABLED`.
 *
 * @module
 */

/** The spellings of `true` that pydantic accepts, so frontend and backend agree. */
const TRUE = ['1', 'on', 't', 'true', 'y', 'yes'];

/**
 * `true` if `value` of `REGISTRATION_ENABLED` opens sign-up. Only hides or shows the
 * form: the backend enforces the same variable and answers 403 while it is closed.
 */
export function registrationEnabled(value: string | undefined): boolean {
  return TRUE.includes(value?.trim().toLowerCase() ?? '');
}
