/**
 * Display labels and formatters shared by the gift list and the gift idea detail page.
 * Holds no server imports, so pages and components can use it in the browser.
 *
 * @module
 */
import type { components } from '$lib/api/schema';

type GiftCategory = components['schemas']['GiftCategory'];
type TaskStatus = components['schemas']['TaskStatus'];

/** Progress of a gifting: `idea`, `planned`, `acquired` or `given`. */
export type GiftingStatus = components['schemas']['GiftingStatus'];

// Q-07: always show the status as text and symbol; colour is only an addition.
export const GIFTING_STATUS: Record<GiftingStatus, { label: string; icon: string }> = {
  idea: { label: 'Idee', icon: '○' },
  planned: { label: 'Geplant', icon: '◔' },
  acquired: { label: 'Besorgt', icon: '◕' },
  given: { label: 'Verschenkt', icon: '✓' }
};
export const GIFTING_STATUS_ORDER = Object.keys(GIFTING_STATUS) as GiftingStatus[];
export const GIFTING_STATUS_CLASS: Record<GiftingStatus, string> = {
  idea: 'border-gray-400 text-gray-700',
  planned: 'border-blue-700 text-blue-800',
  acquired: 'border-amber-700 text-amber-800',
  given: 'border-green-700 text-green-800'
};

export const TASK_STATUS: Record<TaskStatus, { label: string; icon: string }> = {
  open: { label: 'Offen', icon: '○' },
  in_progress: { label: 'In Bearbeitung', icon: '◔' },
  done: { label: 'Erledigt', icon: '✓' },
  discarded: { label: 'Verworfen', icon: '✕' }
};
export const TASK_STATUS_ORDER = Object.keys(TASK_STATUS) as TaskStatus[];

export const CATEGORIES: Record<GiftCategory, string> = {
  books: 'Bücher',
  games: 'Spiele',
  experience: 'Erlebnis',
  clothing: 'Kleidung',
  tech: 'Technik',
  food: 'Essen & Trinken',
  home: 'Wohnen',
  voucher: 'Gutschein',
  other: 'Sonstiges'
};

/** Turns an ISO date (`2026-12-24`) into the German form (`24.12.2026`). */
export const formatDate = (iso: string | null) => (iso ? iso.split('-').reverse().join('.') : '');

// Prices come from the API with a decimal point; the form shows them with a decimal comma.
export const formatPrice = (price: string | number | null | undefined) =>
  price === null || price === undefined ? '' : String(price).replace('.', ',');

/** One line per gift idea, e.g. „3 Beschenkungen: 2× ◔ Geplant · ✓ Verschenkt“. */
export function giftingSummary(statuses: GiftingStatus[]): string {
  if (statuses.length === 0) return 'Noch keine Beschenkung';
  const parts = GIFTING_STATUS_ORDER.flatMap((status) => {
    const count = statuses.filter((s) => s === status).length;
    if (count === 0) return [];
    const { icon, label } = GIFTING_STATUS[status];
    return [`${count > 1 ? `${count}× ` : ''}${icon} ${label}`];
  });
  const noun = statuses.length === 1 ? 'Beschenkung' : 'Beschenkungen';
  return `${statuses.length} ${noun}: ${parts.join(' · ')}`;
}
