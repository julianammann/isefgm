<script lang="ts">
  import { pageCount } from '$lib/pagination';

  type Props = {
    page: number;
    total: number;
    /** Returns the already resolved URL of a page. */
    href: (page: number) => string;
  };

  let { page, total, href }: Props = $props();

  const last = $derived(pageCount(total));
  const pages = $derived(Array.from({ length: last }, (_, i) => i + 1));
</script>

{#if last > 1}
  <!-- eslint-disable svelte/no-navigation-without-resolve -- hrefs are resolved by the caller -->
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
  <!-- eslint-enable svelte/no-navigation-without-resolve -->
{/if}
