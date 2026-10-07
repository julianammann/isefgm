/**
 * Persons data access (F-02).
 *
 * Temporary in-memory mock until the backend endpoints (#20) exist. All functions already
 * take the API client, so call sites stay unchanged when switching to `locals.api`.
 *
 * @module
 */

// TODO(#20): replace with generated types
// import type { components } from '$lib/api/schema';
// export type Person = components['schemas']['PersonRead'];
// export type PersonInput = components['schemas']['PersonCreate'];
export type Person = {
  id: string;
  name: string;
  birthday: string | null;
  notes: string | null;
};
export type PersonInput = Omit<Person, 'id'>;

type Api = App.Locals['api'];

/** Outcome of a data access call; on failure carries the HTTP status and a display message. */
export type Result<T> = { ok: true; data: T } | { ok: false; status: number; message: string };

// TODO(#20): remove mock store, call `api` instead
let store: Person[] = [
  { id: '1', name: 'Anna Beispiel', birthday: '1990-04-12', notes: null },
  { id: '2', name: 'Ben Muster', birthday: null, notes: 'mag Bücher' }
];

const notFound = { ok: false, status: 404, message: 'Person nicht gefunden.' } as const;

/** Returns all persons of the current account. */
// export async function listPersons(_api: Api): Promise<Result<Person[]>> {
//   return { ok: true, data: structuredClone(store) };
// }
export async function listPersons(api: Api): Promise<Result<Person[]>> {
  void api;
  return { ok: true, data: structuredClone(store) };
}

/** Creates a person and returns it with its new id. */
export async function createPerson(_api: Api, input: PersonInput): Promise<Result<Person>> {
  const person = { id: crypto.randomUUID(), ...input };
  store.push(person);
  return { ok: true, data: structuredClone(person) };
}

/** Replaces the data of an existing person; 404 if the id is unknown. */
export async function updatePerson(
  _api: Api,
  id: string,
  input: PersonInput
): Promise<Result<Person>> {
  const index = store.findIndex((p) => p.id === id);
  if (index === -1) return notFound;
  store[index] = { id, ...input };
  return { ok: true, data: structuredClone(store[index]) };
}

/** Deletes a person; 404 if the id is unknown. */
export async function deletePerson(_api: Api, id: string): Promise<Result<null>> {
  const before = store.length;
  store = store.filter((p) => p.id !== id);
  return store.length < before ? { ok: true, data: null } : notFound;
}
