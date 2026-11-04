<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import Pagination from '#lib/components/Pagination.svelte';
  import { actionUrl, pageQuery } from '#lib/pagination.js';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();
</script>

<svelte:head
  ><title
    >{data.page > 1
      ? `Ideen – Seite ${data.page} – Geschenke-Manager`
      : 'Ideen – Geschenke-Manager'}</title
  ></svelte:head
>

<main class="mx-auto max-w-4xl p-8">
  <h1 class="text-2xl font-bold">Ideen</h1>
  <p class="mt-2 text-sm text-gray-600">
    Geschenke, die in einem Konto schon verschenkt wurden. Zu sehen ist nur der Titel, nicht an wen,
    von wem oder wann.
  </p>
  {#if data.success}<p role="status" class="mt-4 text-sm text-green-800">{data.success}</p>{/if}
  {#if form?.message}<p role="alert" class="mt-4 text-sm text-red-800">{form.message}</p>{/if}
  {#if data.titles.length === 0}
    <p class="mt-4 text-sm text-gray-600">Noch keine verschenkten Geschenke.</p>
  {:else}
    <ul class="mt-4 flex flex-col gap-3">
      {#each data.titles as title (title)}
        <li class="flex flex-wrap items-center justify-between gap-3 rounded border p-4">
          <span>{title}</span>
          <form method="POST" action={actionUrl('adopt', data.page)} use:enhance>
            <input type="hidden" name="title" value={title} />
            <button type="submit" class="text-sm underline"
              >Übernehmen<span class="sr-only">: {title}</span></button
            >
          </form>
        </li>
      {/each}
    </ul>
  {/if}
  <Pagination page={data.page} total={data.total} href={(p) => resolve(`ideas${pageQuery(p)}`)} />
</main>
