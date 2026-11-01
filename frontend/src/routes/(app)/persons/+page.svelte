<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import Pagination from '$lib/components/Pagination.svelte';
  import PersonFormDialog from '$lib/components/PersonFormDialog.svelte';
  import { actionUrl, pageQuery } from '$lib/pagination';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const isEdit = $derived(data.editing !== null);
  const values = $derived(
    form?.values ?? data.editing ?? { name: '', birthday: null, relationship: null, notes: null }
  );
  const errors = $derived(form?.errors ?? {});

  let showForm = $state(false);
  let previousEditId = $state<string | null>(null);
  let dialog: HTMLDialogElement | null = null;
  let toDelete = $state<{ id: string; name: string } | null>(null);

  /** Drops `?edit` when the edit dialog is closed with Escape or Abbrechen. */
  function leaveEdit() {
    if (page.url.searchParams.has('edit')) {
      goto(resolve(`/persons${pageQuery(data.page)}`), {
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

  function askDelete(person: { id: string; name: string }) {
    toDelete = person;
    dialog?.showModal();
  }
</script>

<svelte:head
  ><title
    >{data.page > 1
      ? `Personen – Seite ${data.page} – Geschenke-Manager`
      : 'Personen – Geschenke-Manager'}</title
  ></svelte:head
>

<main class="mx-auto max-w-4xl p-8">
  <h1 class="text-2xl font-bold">Personen</h1>

  <section class="mt-10" aria-labelledby="list-heading">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="list-heading" class="font-semibold">Übersicht</h2>
      {#if !isEdit}
        <button
          type="button"
          class="rounded bg-black px-4 py-2 text-white"
          aria-haspopup="dialog"
          aria-controls="person-form-dialog"
          onclick={openForm}
        >
          Person hinzufügen
        </button>
      {/if}
    </div>
    {#if data.success}<p role="status" class="mt-2 text-sm text-green-800">{data.success}</p>{/if}
    {#if form?.deleteMessage}
      <p role="alert" class="mt-2 text-sm text-red-800">{form.deleteMessage}</p>
    {/if}
    {#if data.persons.length === 0}
      <p class="mt-2 text-sm">Noch keine Personen angelegt.</p>
    {:else}
      <ul class="mt-4 flex flex-col gap-3">
        {#each data.persons as person (person.id)}
          <li class="rounded border p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 class="text-lg font-semibold">
                  <a href={resolve(`/persons/${person.id}`)} class="font-bold underline"
                    >{person.name}</a
                  >
                </h3>
                <p class="mt-1 text-sm text-gray-600">
                  {#if person.birthday}
                    <span class="text-sm text-gray-600">{person.birthday}</span>{/if}
                  {#if person.relationship}
                    <span class="ml-2 text-sm text-gray-600">{person.relationship}</span>
                  {/if}
                </p>
              </div>
              <div class="flex items-center gap-4">
                <a
                  href={resolve(`/persons${pageQuery(data.page, { edit: person.id })}`)}
                  class="text-sm underline"
                  >Bearbeiten
                  <span class="sr-only">: {person.name}</span>
                </a>
                <button
                  type="button"
                  class="text-sm text-red-800 underline"
                  onclick={() => askDelete(person)}
                >
                  Löschen<span class="sr-only">: {person.name}</span>
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
      href={(p) => resolve(`/persons${pageQuery(p)}`)}
    />
  </section>

  <dialog
    bind:this={dialog}
    aria-labelledby="dialog-heading"
    class="m-auto rounded border p-6 backdrop:bg-black/40"
  >
    <h2 id="dialog-heading" class="font-semibold">Person löschen?</h2>
    <p class="mt-2 text-sm">
      „{toDelete?.name}“ wird mit allen zugehörigen Daten endgültig gelöscht.
    </p>
    <form
      method="POST"
      action={actionUrl('delete', data.page)}
      class="mt-4 flex justify-end gap-3"
      use:enhance={() =>
        async ({ update }) => {
          dialog?.close();
          await update();
        }}
    >
      <input type="hidden" name="id" value={toDelete?.id} />
      <button type="button" class="rounded border px-4 py-2" onclick={() => dialog?.close()}>
        Abbrechen
      </button>
      <button type="submit" class="rounded bg-red-700 px-4 py-2 text-white">Löschen</button>
    </form>
  </dialog>

  <!-- data.persons is a new array whenever the page data reloads: re-create the dialog then, so
       a saved person's input is gone; a failed submit keeps the dialog and its focus. -->
  {#key data.persons}
    <PersonFormDialog
      bind:open={showForm}
      action={actionUrl(isEdit ? 'update' : 'create', data.page)}
      editId={data.editing?.id ?? null}
      {values}
      {errors}
      message={form?.message ?? null}
      keepPosition={false}
      onclose={leaveEdit}
    />
  {/key}
</main>
