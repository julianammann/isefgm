/**
 * Full list (`/full-list`, F-15): the account's people, gift ideas and past gifts as one
 * self-contained HTML document, opened in a new tab or downloaded from the account page.
 *
 * @module
 */
import { render } from 'svelte/server';
import type { RequestHandler } from './$types';

import { send, unwrap } from '#lib/server/result.js';
import FullList from './FullList.svelte';

/**
 * Renders the full list without the app layout or app scripts, so the downloaded file works
 * on its own; its styles travel inside the document. A backend failure becomes an error page.
 */
export const GET: RequestHandler = async ({ locals }) => {
  const list = unwrap(await send(locals.api.GET('/api/v1/full-list'), {}));
  const { head, body } = render(FullList, { props: { list } });
  const html = `<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
${head}
</head>
<body>
${body}
</body>
</html>
`;
  return new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'private, no-store' }
  });
};
