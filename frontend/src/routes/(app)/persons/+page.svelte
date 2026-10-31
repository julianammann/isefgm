<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import Pagination from '$lib/components/Pagination.svelte';
  import { actionUrl, pageQuery } from '$lib/pagination';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const isEdit = $derived(data.editing !== null);
  const values = $derived(
    form?.values ?? data.editing ?? { name: '', birthday: null, relationship: null, notes: null }
  );
  const errors = $derived(form?.errors ?? {});

  let showForm = $state(false);
  let formDialog: HTMLDialogElement | undefined = $state();
  let previousEditId = $state<string | null>(null);
  let dialog: HTMLDialogElement | null = null;
  let toDelete = $state<{ id: string; name: string } | null>(null);

  $effect(() => {
    const editId = data.editing?.id ?? null;
    if (previousEditId && !editId) showForm = false;
    if (editId && editId !== previousEditId) showForm = true;
    previousEditId = editId;
    if (showForm && formDialog && !formDialog.open) formDialog.showModal();
    if (!isEdit && !showForm && formDialog?.open) formDialog.close();
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
      <ul class="mt-4 divide-y rounded border">
        {#each data.persons as person (person.id)}
          <li class="flex items-center gap-4 p-3">
            <span class="flex-1">
              <span class="font-bold">{person.name}</span>
              {#if person.birthday}<span class="ml-2 text-sm text-gray-600">{person.birthday}</span
                >{/if}
              {#if person.relationship}
                <span class="ml-2 text-sm text-gray-600">{person.relationship}</span>
              {/if}
            </span>
            <a
              href={resolve(`/persons${pageQuery(data.page, { edit: person.id })}`)}
              class="text-sm underline"
            >
              Bearbeiten<span class="sr-only">: {person.name}</span>
            </a>
            <button
              type="button"
              class="text-sm text-red-800 underline"
              onclick={() => askDelete(person)}
            >
              Löschen<span class="sr-only">: {person.name}</span>
            </button>
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

  <dialog
    id="person-form-dialog"
    bind:this={formDialog}
    aria-labelledby="form-heading"
    class="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-lg rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
    onclose={() => (showForm = false)}
  >
    <h2 id="form-heading" class="font-semibold">
      {isEdit ? 'Person bearbeiten' : 'Person anlegen'}
    </h2>
    {#key data}
      <form
        method="POST"
        action={isEdit ? actionUrl('update', data.page) : actionUrl('create', data.page)}
        use:enhance={() =>
          async ({ result, update }) => {
            if (result.type === 'redirect') {
              showForm = false;
              formDialog?.close();
            }
            await update();
          }}
        novalidate
        class="mt-4 flex flex-col gap-3"
      >
        {#if form?.message}<p role="alert" class="text-sm text-red-800">{form.message}</p>{/if}
        {#if isEdit}<input type="hidden" name="id" value={data.editing?.id} />{/if}

        <label for="name" class="text-sm font-medium">Name</label>
        <input
          id="name"
          name="name"
          required
          value={values.name}
          class="rounded border px-3 py-2"
          aria-invalid={errors.name ? 'true' : undefined}
          aria-describedby={errors.name ? 'name-error' : undefined}
        />
        {#if errors.name}<p id="name-error" class="text-sm text-red-800">{errors.name}</p>{/if}

        <label for="birthday" class="text-sm font-medium">Geburtstag (optional)</label>
        <input
          id="birthday"
          name="birthday"
          type="date"
          value={values.birthday ?? ''}
          class="rounded border px-3 py-2"
          aria-invalid={errors.birthday ? 'true' : undefined}
          aria-describedby={errors.birthday ? 'birthday-error' : undefined}
        />
        {#if errors.birthday}
          <p id="birthday-error" class="text-sm text-red-800">{errors.birthday}</p>
        {/if}

        <label for="relationship" class="text-sm font-medium">Beziehung (optional)</label>
        <input
          id="relationship"
          name="relationship"
          maxlength="100"
          value={values.relationship ?? ''}
          class="rounded border px-3 py-2"
          aria-invalid={errors.relationship ? 'true' : undefined}
          aria-describedby={errors.relationship ? 'relationship-error' : undefined}
        />
        {#if errors.relationship}
          <p id="relationship-error" class="text-sm text-red-800">{errors.relationship}</p>
        {/if}

        <label for="notes" class="text-sm font-medium">Notizen (optional)</label>
        <textarea
          id="notes"
          name="notes"
          maxlength="2000"
          class="rounded border px-3 py-2"
          aria-invalid={errors.notes ? 'true' : undefined}
          aria-describedby={errors.notes ? 'notes-error' : undefined}>{values.notes ?? ''}</textarea
        >
        {#if errors.notes}<p id="notes-error" class="text-sm text-red-800">{errors.notes}</p>{/if}

        <div class="flex items-center gap-4">
          <button type="submit" class="rounded bg-black px-4 py-2 text-white">
            {isEdit ? 'Speichern' : 'Anlegen'}
          </button>
          {#if isEdit}
            <a href={resolve(`/persons${pageQuery(data.page)}`)} class="rounded border px-4 py-2"
              >Abbrechen</a
            >
          {:else}
            <button
              type="button"
              class="rounded border px-4 py-2"
              onclick={() => formDialog?.close()}
            >
              Abbrechen
            </button>
          {/if}
        </div>
      </form>
    {/key}
  </dialog>
</main>
