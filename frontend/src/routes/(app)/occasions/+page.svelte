<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import Pagination from '$lib/components/Pagination.svelte';
  import { actionUrl, pageQuery } from '$lib/pagination';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const isEdit = $derived(data.editOccasion !== null);
  const birthdayTypeId = $derived(
    data.occasionTypes.find((occasionType) => occasionType.name === 'Geburtstag')?.id ?? null
  );
  const values = $derived(
    form?.values ??
      data.editOccasion ?? {
        name: '',
        date: '',
        occasion_type_id: null,
        person_ids: [],
        recurrence: 'none' as const
      }
  );
  const errors = $derived(form?.errors ?? {});
  // shortcut: sorts within one page only, remove once the backend sorts by month/day (#131).
  const sortedOccasions = $derived(
    [...data.occasions].sort((first, second) => {
      const firstMonthDay = first.date.slice(5);
      const secondMonthDay = second.date.slice(5);
      return firstMonthDay.localeCompare(secondMonthDay);
    })
  );

  /** Resolved list URL that keeps the current page. */
  const listHref = (extra?: Record<string, string>) =>
    resolve('/occasions') + pageQuery(data.page, extra);

  function formatDate(date: string): string {
    const [year, month, day] = date.split('-');
    return `${day}.${month}.${year}`;
  }

  let showForm = $state(false);
  let formDialog: HTMLDialogElement | undefined = $state();
  let previousEditId = $state<string | null>(null);
  let dialog: HTMLDialogElement | null = null;
  let toDelete = $state<{ id: string; name: string } | null>(null);

  $effect(() => {
    const editId = data.editOccasion?.id ?? null;
    if (previousEditId && !editId) showForm = false;
    if (editId && editId !== previousEditId) showForm = true;
    previousEditId = editId;
    if (showForm && formDialog && !formDialog.open) formDialog.showModal();
    if (!isEdit && !showForm && formDialog?.open) formDialog.close();
  });

  function openForm() {
    showForm = true;
  }

  function askDelete(occasion: { id: string; name: string }) {
    toDelete = occasion;
    dialog?.showModal();
  }
</script>

<svelte:head><title>Anlässe – Geschenke-Manager</title></svelte:head>

<main class="mx-auto max-w-4xl p-8">
  <h1 class="text-2xl font-bold">Anlässe</h1>

  <section class="mt-10" aria-labelledby="list-heading">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="list-heading" class="font-semibold">Übersicht</h2>
      {#if !isEdit}
        <button
          type="button"
          class="rounded bg-black px-4 py-2 text-white"
          aria-haspopup="dialog"
          aria-controls="occasion-form-dialog"
          onclick={openForm}
        >
          Anlass anlegen
        </button>
      {/if}
    </div>
    {#if data.occasions.length === 0}
      <p class="mt-4 text-sm text-gray-600">Keine Anlässe vorhanden.</p>
    {:else}
      <ul class="mt-4 flex flex-col gap-3">
        {#each sortedOccasions as occasion (occasion.id)}
          <li class="flex items-center justify-between rounded border px-4 py-2">
            <div>
              <p class="font-medium">{occasion.name}</p>
              <p class="text-sm text-gray-600">
                {formatDate(occasion.date)} · {occasion.recurrence === 'yearly'
                  ? 'Jährlich'
                  : 'Einmalig'}
              </p>
              {#if occasion.people.length}
                <p class="text-sm text-gray-600">
                  Für: {occasion.people.map((person) => person.name).join(', ')}
                </p>
              {/if}
            </div>
            {#if birthdayTypeId && occasion.occasion_type_id === birthdayTypeId}
              <span class="text-sm text-gray-600">(Geburtstag wird über die Person gepflegt)</span>
            {:else}
              <div class="flex items-center gap-2">
                <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- listHref resolves -->
                <a href={listHref({ edit: occasion.id })} class="text-sm underline">Bearbeiten</a>
                <button
                  type="button"
                  class="text-sm text-red-800 underline"
                  onclick={() => askDelete(occasion)}
                >
                  Löschen<span class="sr-only">: {occasion.name}</span>
                </button>
              </div>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
    <Pagination
      page={data.page}
      total={data.total}
      href={(p) => resolve('/occasions') + pageQuery(p)}
    />
  </section>

  <dialog
    bind:this={dialog}
    class="m-auto rounded border p-6 backdrop:bg-black/40"
    aria-labelledby="delete-dialog-heading"
  >
    <h2 id="delete-dialog-heading" class="font-semibold">Anlass löschen</h2>
    <p class="mt-2 text-sm">
      Sind Sie sicher, dass Sie den Anlass
      <span class="font-medium">{toDelete?.name}</span> löschen möchten? Dies kann nicht rückgängig gemacht
      werden.
    </p>
    <form
      method="POST"
      action={actionUrl('delete', data.page)}
      class="mt-4 flex justify-end gap-3"
      use:enhance={() =>
        async ({ result, update }) => {
          if (result.type === 'redirect') dialog?.close();
          await update();
        }}
    >
      {#if form?.errors?.general}
        <p role="alert" class="mr-auto text-sm text-red-800">{form.errors.general}</p>
      {/if}
      <input type="hidden" name="id" value={toDelete?.id} />
      <button type="button" class="rounded border px-4 py-2" onclick={() => dialog?.close()}>
        Abbrechen
      </button>
      <button type="submit" class="rounded bg-red-700 px-4 py-2 text-white">Löschen</button>
    </form>
  </dialog>

  {#if data.successMessage}
    <p role="status" class="mt-4 text-sm text-green-800">{data.successMessage}</p>
  {/if}

  <dialog
    id="occasion-form-dialog"
    bind:this={formDialog}
    aria-labelledby="form-heading"
    class="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-lg rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
    onclose={() => (showForm = false)}
  >
    <h2 id="form-heading" class="font-semibold">
      {isEdit ? 'Anlass bearbeiten' : 'Anlass anlegen'}
    </h2>
    {#key data}
      <form
        method="POST"
        action={actionUrl(isEdit ? 'update' : 'create', data.page)}
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
        {#if errors.general}<p role="alert" class="text-sm text-red-800">{errors.general}</p>{/if}
        {#if isEdit}<input type="hidden" name="id" value={data.editOccasion?.id} />{/if}

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

        <label for="date" class="text-sm font-medium">Datum</label>
        <input
          id="date"
          name="date"
          type="date"
          required
          value={values.date}
          class="rounded border px-3 py-2"
          aria-invalid={errors.date ? 'true' : undefined}
          aria-describedby={errors.date ? 'date-error' : undefined}
        />
        {#if errors.date}<p id="date-error" class="text-sm text-red-800">{errors.date}</p>{/if}

        <label for="occasion_type_id" class="text-sm font-medium">Anlasstyp</label>
        <select
          id="occasion_type_id"
          name="occasion_type_id"
          value={values.occasion_type_id ?? ''}
          class="rounded border px-3 py-2"
        >
          <option value="">Kein Typ</option>
          {#each data.occasionTypes as occasionType (occasionType.id)}
            <option value={occasionType.id} disabled={occasionType.name === 'Geburtstag'}>
              {occasionType.name}{occasionType.name === 'Geburtstag'
                ? ' (über Person gepflegt)'
                : ''}
            </option>
          {/each}
        </select>
        <fieldset class="flex flex-col gap-2">
          <legend class="text-sm font-medium">Personen (optional)</legend>
          {#if data.people.length === 0}
            <p class="text-sm text-gray-600">
              Noch keine Personen angelegt. Du kannst den Anlass auch ohne Zuordnung speichern.
            </p>
          {:else}
            <details class="flex flex-col gap-1">
              <summary class="cursor-pointer rounded border px-3 py-2">
                {#if (values.person_ids ?? []).length > 0}
                  {data.people
                    .filter((person) => (values.person_ids ?? []).includes(person.id))
                    .map((person) => person.name)
                    .join(', ')}
                {:else}
                  Personen auswählen
                {/if}
              </summary>
              <div class="max-h-30 overflow-y-auto rounded border bg-white p-3">
                {#each data.people as person (person.id)}
                  <label class="flex items-center gap-2 py-1">
                    <input
                      type="checkbox"
                      name="person_ids"
                      value={person.id}
                      checked={(values.person_ids ?? []).includes(person.id)}
                    />
                    {person.name}
                  </label>
                {/each}
              </div>
            </details>
          {/if}
        </fieldset>

        <label for="recurrence" class="text-sm font-medium">Wiederholung</label>
        <select
          id="recurrence"
          name="recurrence"
          value={values.recurrence}
          class="rounded border px-3 py-2"
          aria-invalid={errors.recurrence ? 'true' : undefined}
          aria-describedby={errors.recurrence ? 'recurrence-error' : undefined}
        >
          <option value="none">Einmalig</option>
          <option value="yearly">Jährlich</option>
        </select>
        {#if errors.recurrence}
          <p id="recurrence-error" class="text-sm text-red-800">{errors.recurrence}</p>
        {/if}

        <div class="flex items-center gap-4">
          <button type="submit" class="rounded bg-black px-4 py-2 text-white">
            {isEdit ? 'Speichern' : 'Anlegen'}
          </button>
          {#if isEdit}
            <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- listHref resolves -->
            <a href={listHref()} class="text-sm underline">Abbrechen</a>
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
