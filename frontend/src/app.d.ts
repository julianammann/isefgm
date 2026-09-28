import type { ApiClient, User } from '$lib/api/client';

declare global {
  namespace App {
    // interface Error {}
    interface Locals {
      api: ApiClient;
      /** Resolved once per request in hooks.server.ts from the session cookie. */
      user: User | null;
      /** The backend could not say who is logged in (unreachable or 5xx). */
      authUnavailable: boolean;
    }
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}

export {};
