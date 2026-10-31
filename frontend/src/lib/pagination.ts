/** Pagination helpers shared by the list pages; browser-safe, no server imports. */

export const PAGE_SIZE = 200;

/** Highest page whose offset `(page - 1) * PAGE_SIZE` is still a safe integer. */
export const MAX_PAGE = Math.floor(Number.MAX_SAFE_INTEGER / PAGE_SIZE);

/** Page number from `?page=`; anything that is not a positive integer is page 1. */
export function parsePage(url: URL): number {
  const value = url.searchParams.get('page') ?? '';
  return /^[1-9]\d*$/.test(value) ? Math.min(Number(value), MAX_PAGE) : 1;
}

/** Number of pages for `total` entries; at least 1. */
export function pageCount(total: number): number {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

/** Query string for a list page plus extra params, page 1 omitted; '' when nothing is left. */
export function pageQuery(page: number, extra: Record<string, string> = {}): '' | `?${string}` {
  const params = new URLSearchParams(page > 1 ? { page: String(page) } : {});
  for (const [key, value] of Object.entries(extra)) params.set(key, value);
  const query = params.toString();
  return query ? `?${query}` : '';
}

/** Form action URL that carries the page, e.g. `?page=3&/update`; the page also works without JavaScript. */
export function actionUrl(name: string, page: number): string {
  return page > 1 ? `?page=${page}&/${name}` : `?/${name}`;
}
