<script lang="ts">
  import type { ResolvedPathname } from '$app/types';
  import { pageCount } from '$lib/pagination';

  type Props = {
    page: number;
    total: number;
    /** Returns the already resolved URL of a page. */
    href: (page: number) => ResolvedPathname;
  };

  let { page, total, href }: Props = $props();

  // shortcut: every page number is shown, no ellipsis; add one when accounts exceed ~10 pages.
  const last = $derived(pageCount(total));
  const pages = $derived(Array.from({ length: last }, (_, i) => i + 1));
</script>

{#if last > 1}
  <nav aria-label="Seiten" class="mt-6 flex flex-wrap items-center gap-2">
    {#if page > 1}
      <a href={href(page - 1)} class="rounded px-3 py-1 underline">Zurück</a>
    {/if}
    {#each pages as p (p)}
      <a
        href={href(p)}
        aria-label="Seite {p}"
        aria-current={p === page ? 'page' : undefined}
        class="rounded px-3 py-1 underline aria-[current=page]:font-bold aria-[current=page]:no-underline"
        >{p}</a
      >
    {/each}
    {#if page < last}
      <a href={href(page + 1)} class="rounded px-3 py-1 underline">Weiter</a>
    {/if}
  </nav>
{/if}
