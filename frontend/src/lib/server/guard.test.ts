import { describe, expect, it } from 'vitest';

import type { User } from '$lib/api/client';

import { guard, type Auth } from './guard.ts';

const anna: User = {
  id: '0190c6f4-0000-7000-8000-000000000000',
  email: 'anna@example.org',
  display_name: 'Anna',
  created_at: '2026-09-27T12:00:00Z'
};
const loggedIn: Auth = { state: 'user', user: anna };
const anonymous: Auth = { state: 'anonymous' };
const unknown: Auth = { state: 'unknown' };
const url = (path: string) => new URL(path, 'http://app.test');

describe('guard', () => {
  it('sends anonymous users from (app) to the login with the original target', () => {
    expect(guard('/(app)/account', anonymous, url('/account?tab=1'))).toEqual({
      action: 'redirect',
      location: '/login?next=%2Faccount%3Ftab%3D1'
    });
  });

  it('lets logged-in users into (app)', () => {
    expect(guard('/(app)/account', loggedIn, url('/account'))).toEqual({ action: 'pass' });
  });

  it('answers (app) with 503 when the login state is unknown, not with the login page', () => {
    expect(guard('/(app)', unknown, url('/'))).toEqual({ action: 'unavailable' });
  });

  it('sends logged-in users away from login and registration', () => {
    expect(guard('/(auth)/login', loggedIn, url('/login'))).toEqual({
      action: 'redirect',
      location: '/'
    });
    expect(guard('/(auth)/register', anonymous, url('/register'))).toEqual({ action: 'pass' });
    expect(guard('/(auth)/login', unknown, url('/login'))).toEqual({ action: 'pass' });
  });

  it('leaves public and unknown routes alone', () => {
    expect(guard('/logout', anonymous, url('/logout'))).toEqual({ action: 'pass' });
    expect(guard('/api/[...path]', unknown, url('/api/v1/auth/me'))).toEqual({ action: 'pass' });
    expect(guard(null, anonymous, url('/nope'))).toEqual({ action: 'pass' });
  });
});
