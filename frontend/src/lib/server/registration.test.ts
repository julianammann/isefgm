import { describe, expect, it } from 'vitest';

import { registrationEnabled } from './registration.ts';

describe('registrationEnabled', () => {
  it.each(['true', 'TRUE', 'True', '1', 'yes', 'y', 'on', 't'])(
    'opens sign-up for %j, as the backend does',
    (value) => {
      expect(registrationEnabled(value)).toBe(true);
    }
  );

  it.each([undefined, '', 'false', '0', 'no', 'off', 'enabled'])(
    'keeps sign-up closed for %j',
    (value) => {
      expect(registrationEnabled(value)).toBe(false);
    }
  );
});
