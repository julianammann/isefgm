<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const isEdit = $derived(data.editOccasion !== null);
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

  let dialog: HTMLDialogElement | null = null;
  let toDelete = $state<{ id: string; name: string } | null>(null);

  function askDelete(occasion: { id: string; name: string }) {
    toDelete = occasion;
    dialog?.showModal();
  }
</script>

<svelte:head><title>Anlässe – Geschenke-Manager</title></svelte:head>

<main class="mx-auto max-w-4xl p-8">
  <h1 class="text-2xl font-bold">Anlässe</h1>

  {#if data.successMessage}
    <p role="status" class="mt-4 text-sm text-green-800">{data.successMessage}</p>
  {/if}

  <section class="mt-10 rounded border p-4" aria-labelledby="form-heading">
    <h2 id="form-heading" class="font-semibold">
      {isEdit ? 'Anlass bearbeiten' : 'Anlass anlegen'}
    </h2>
    {#key data}
      <form
        method="POST"
        action={isEdit ? '?/update' : '?/create'}
        use:enhance
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
        <!-- To Do when person is integrated -->
        <!-- <fieldset class="flex flex-col gap-2">
            <legend class="text-sm font-medium">Personen</legend>

            {#each data.person as person (person.id)}
                <label class="flex items-center gap-2">
                <input
                    type="checkbox"
                    name="person_ids"
                    value={person.id}
                    checked={(values.person_ids ?? []).includes(person.id)}
                />
                {person.name}
                </label>
            {/each}
        </fieldset> -->

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
            <a href={resolve('/occasions')} class="text-sm underline">Abbrechen</a>
          {/if}
        </div>
      </form>
    {/key}
  </section>

  <section class="mt-10 rounded border p-4" aria-labelledby="list-heading">
    <h2 id="list-heading" class="font-semibold">Anlässe</h2>
    {#if data.occasions.length === 0}
      <p class="mt-4 text-sm text-gray-600">Keine Anlässe vorhanden.</p>
    {:else}
      <ul class="mt-4 flex flex-col gap-3">
        {#each data.occasions as occasion (occasion.id)}
          <li class="flex items-center justify-between rounded border px-4 py-2">
            <div>
              <p class="font-medium">{occasion.name}</p>
              <p class="text-sm text-gray-600">
                {occasion.date} · {occasion.recurrence === 'yearly' ? 'Jährlich' : 'Einmalig'}
              </p>
              {#if occasion.people.length}
                <p class="text-sm text-gray-600">
                  Für: {occasion.people.map((person) => person.name).join(', ')}
                </p>
              {/if}
            </div>
            <div class="flex items-center gap-2">
              <a
                href={resolve(`/occasions?edit=${occasion.id}`)}
                class="rounded border px-4 py-2 text-blue-700">Bearbeiten</a
              >
              <button
                type="button"
                class="rounded border px-4 py-2 text-red-700"
                onclick={() => askDelete(occasion)}
              >
                Löschen<span class="sr-only">: {occasion.name}</span>
              </button>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
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
      action="?/delete"
      class="mt-4 flex justify-end gap-3"
      use:enhance={() =>
        async ({ result, update }) => {
          if (result.type === 'redirect') dialog?.close();
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
</main>
