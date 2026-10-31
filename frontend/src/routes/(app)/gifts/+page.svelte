<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import Pagination from '$lib/components/Pagination.svelte';
  import GiftFormDialog from '$lib/components/GiftFormDialog.svelte';
  import { CATEGORIES, giftingSummary } from '$lib/display';
  import { actionUrl, pageQuery } from '$lib/pagination';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const isEdit = $derived(data.editing !== null);
  const values = $derived(
    form?.values ??
      data.editing ?? {
        title: '',
        description: null,
        category: 'other' as const,
        price_from: null,
        price_to: null,
        currency: null,
        person_ids: [],
        occasion_ids: []
      }
  );
  const errors = $derived(form?.errors ?? {});

  let showForm = $state(false);
  let previousEditId = $state<string | null>(null);
  let deleteDialog: HTMLDialogElement | null = null;
  let toDelete = $state<{ id: string; title: string } | null>(null);

  /** Drops `?edit` when the edit dialog is closed with Escape or Abbrechen. */
  function leaveEdit() {
    if (page.url.searchParams.has('edit')) {
      // eslint-disable-next-line svelte/no-navigation-without-resolve -- resolve() is applied to the path
      goto(resolve('/gifts') + pageQuery(data.page), {
        replaceState: true,
        noScroll: true,
        keepFocus: true
      });
    }
  }

  $effect(() => {
    const editId = data.editing?.id ?? null;
    if (previousEditId && !editId) showForm = false;
    if (editId && editId !== previousEditId) showForm = true;
    previousEditId = editId;
  });

  function openForm() {
    showForm = true;
  }

  function askDelete(gift: { id: string; title: string }) {
    toDelete = gift;
    deleteDialog?.showModal();
  }
</script>

<svelte:head><title>Geschenkideen – Geschenke-Manager</title></svelte:head>

<main class="mx-auto max-w-4xl p-8">
  <h1 class="text-2xl font-bold">Geschenkideen</h1>

  <section class="mt-10" aria-labelledby="list-heading">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="list-heading" class="font-semibold">Übersicht</h2>
      {#if !isEdit}
        <button
          type="button"
          class="rounded bg-black px-4 py-2 text-white"
          aria-haspopup="dialog"
          aria-controls="gift-form-dialog"
          onclick={openForm}
        >
          Geschenkidee hinzufügen
        </button>
      {/if}
    </div>
    {#if data.gifts.length === 0}
      <p class="mt-2 text-sm text-gray-600">Noch keine Geschenkideen erfasst.</p>
    {:else}
      <ul class="mt-4 flex flex-col gap-3">
        {#each data.gifts as gift (gift.id)}
          {@const summary = giftingSummary(
            (data.giftingsByGift[gift.id] ?? []).map((g) => g.status)
          )}
          <li class="rounded border p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 class="text-lg font-semibold">
                  <a href={resolve(`/gifts/${gift.id}`)} class="underline">{gift.title}</a>
                </h3>
                <p class="mt-1 text-sm text-gray-600">
                  {CATEGORIES[gift.category]}
                  {#if gift.people.length}
                    · für {gift.people.map((p) => p.name).join(', ')}{/if}
                </p>
                <p class="mt-1 text-sm">
                  {summary.lead}{#each summary.parts as part, i (part.label)}{i
                      ? ' · '
                      : ''}{part.count}<span aria-hidden="true">{part.icon}</span>
                    {part.label}{/each}
                </p>
              </div>
              <div class="flex items-center gap-4">
                <!-- eslint-disable svelte/no-navigation-without-resolve -- resolve() is applied to the path -->
                <a
                  href={resolve('/gifts') + pageQuery(data.page, { edit: gift.id })}
                  class="text-sm underline"
                >
                  Bearbeiten<span class="sr-only">: {gift.title}</span>
                </a>
                <!-- eslint-enable svelte/no-navigation-without-resolve -->
                <button
                  type="button"
                  class="text-sm text-red-800 underline"
                  onclick={() => askDelete(gift)}
                >
                  Löschen<span class="sr-only">: {gift.title}</span>
                </button>
              </div>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
    <Pagination
      page={data.page}
      total={data.total}
      href={(p) => resolve('/gifts') + pageQuery(p)}
    />
  </section>

  <dialog
    bind:this={deleteDialog}
    aria-labelledby="delete-dialog-heading"
    class="m-auto rounded border p-6 backdrop:bg-black/40"
  >
    <h2 id="delete-dialog-heading" class="font-semibold">Geschenkidee löschen?</h2>
    <p class="mt-2 text-sm">
      „{toDelete?.title}“ wird mit allen zugehörigen Daten endgültig gelöscht.
    </p>
    <form
      method="POST"
      action={actionUrl('delete', data.page)}
      class="mt-4 flex justify-end gap-3"
      use:enhance={() =>
        async ({ update }) => {
          deleteDialog?.close();
          await update();
        }}
    >
      <input type="hidden" name="id" value={toDelete?.id} />
      <button type="button" class="rounded border px-4 py-2" onclick={() => deleteDialog?.close()}>
        Abbrechen
      </button>
      <button type="submit" class="rounded bg-red-700 px-4 py-2 text-white">Löschen</button>
    </form>
  </dialog>

  {#if data.success}<p role="status" class="mt-4 text-sm text-green-800">{data.success}</p>{/if}
  {#if form?.deleteMessage}
    <p role="alert" class="mt-4 text-sm text-red-800">{form.deleteMessage}</p>
  {/if}

  <GiftFormDialog
    bind:open={showForm}
    action={actionUrl(isEdit ? 'update' : 'create', data.page)}
    editId={data.editing?.id ?? null}
    {values}
    {errors}
    message={form?.message ?? null}
    people={data.people}
    occasions={data.occasions}
    keepPosition={false}
    onclose={leaveEdit}
  />
</main>
