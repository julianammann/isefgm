<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { onMount } from 'svelte';
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
  let formDialog: HTMLDialogElement | undefined = $state();
  let previousEditId = $state<string | null>(null);
  let deleteDialog: HTMLDialogElement | null = null;
  let toDelete = $state<{ id: string; title: string } | null>(null);

  type Gifting = (typeof data.giftingsByGift)[string][number];

  const isGiftingEdit = $derived(data.editingGifting !== null);
  /** Set by the create buttons; `fresh` ignores the values of an earlier failed submit. */
  let newGifting = $state<{ giftId: string; status: Status } | null>(null);
  let fresh = $state(false);
  const giftingValues = $derived(
    (fresh ? undefined : form?.giftingValues) ??
      (newGifting
        ? {
            gift_id: newGifting.giftId,
            status: newGifting.status,
            person_ids:
              data.gifts.find((gift) => gift.id === newGifting?.giftId)?.people.map((p) => p.id) ??
              [],
            occasion_id: null,
            occasion_date: null,
            given_on: null
          }
        : null) ??
      data.editingGifting ?? {
        gift_id: '',
        status: 'idea' as const,
        person_ids: [],
        occasion_id: null,
        occasion_date: null,
        given_on: null
      }
  );
  const giftingErrors = $derived(fresh ? {} : (form?.giftingErrors ?? {}));
  const giftingTitle = $derived(
    data.gifts.find((gift) => gift.id === giftingValues.gift_id)?.title ?? ''
  );
  // The status select drives which fields are required; it starts from the loaded values.
  let giftingStatus = $derived<Status>(giftingValues.status ?? 'idea');

  let showGiftingForm = $state(false);
  let giftingFormDialog: HTMLDialogElement | undefined = $state();
  let previousGiftingEditId = $state<string | null>(null);
  let deleteGiftingDialog: HTMLDialogElement | null = null;
  let giftingToDelete = $state<Gifting | null>(null);

  type Status = 'idea' | 'planned' | 'acquired' | 'given';
  // Q-07: Status immer als Text + Symbol, Farbe nur zusätzlich.
  const STATUS: Record<Status, { label: string; icon: string }> = {
    idea: { label: 'Idee', icon: '○' },
    planned: { label: 'Geplant', icon: '◔' },
    acquired: { label: 'Besorgt', icon: '◕' },
    given: { label: 'Verschenkt', icon: '✓' }
  };
  const STATUS_ORDER = Object.keys(STATUS) as Status[];
  const STATUS_CLASS: Record<Status, string> = {
    idea: 'border-gray-400 text-gray-700',
    planned: 'border-blue-700 text-blue-800',
    acquired: 'border-amber-700 text-amber-800',
    given: 'border-green-700 text-green-800'
  };

  const CATEGORIES = {
    books: 'Bücher',
    games: 'Spiele',
    experience: 'Erlebnis',
    clothing: 'Kleidung',
    tech: 'Technik',
    food: 'Essen & Trinken',
    home: 'Wohnen',
    voucher: 'Gutschein',
    other: 'Sonstiges'
  } as const;

  let today = $state('');
  onMount(() => {
    today = new Date().toLocaleDateString('sv-SE');
  });
  const formatDate = (iso: string | null) => (iso ? iso.split('-').reverse().join('.') : '');

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

  function askDelete(gift: { id: string; title: string }) {
    toDelete = gift;
    deleteDialog?.showModal();
  }

  $effect(() => {
    const editId = data.editingGifting?.id ?? null;
    if (previousGiftingEditId && !editId) showGiftingForm = false;
    if (editId && editId !== previousGiftingEditId) showGiftingForm = true;
    previousGiftingEditId = editId;
    if (showGiftingForm && giftingFormDialog && !giftingFormDialog.open) {
      giftingFormDialog.showModal();
    }
    if (!isGiftingEdit && !showGiftingForm && giftingFormDialog?.open) giftingFormDialog.close();
  });

  function openGiftingForm(giftId: string, status: Status = 'idea') {
    newGifting = { giftId, status };
    fresh = true;
    showGiftingForm = true;
  }

  function askDeleteGifting(gifting: Gifting) {
    giftingToDelete = gifting;
    deleteGiftingDialog?.showModal();
  }
</script>

<svelte:head><title>Geschenkideen – Geschenke-Manager</title></svelte:head>

<main class="mx-auto max-w-4xl p-8">
  <h1 class="text-2xl font-bold">Geschenkideen</h1>

  <section class="mt-10" aria-labelledby="list-heading">
    <h2 id="list-heading" class="font-semibold">Übersicht</h2>
    {#if data.gifts.length === 0}
      <p class="mt-2 text-sm text-gray-600">Noch keine Geschenkideen erfasst.</p>
    {:else}
      <ul class="mt-4 flex flex-col gap-3">
        {#each data.gifts as gift (gift.id)}
          {@const giftings = data.giftingsByGift[gift.id] ?? []}
          <li class="rounded border p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 class="text-lg font-semibold">{gift.title}</h3>
                <p class="mt-1 text-sm text-gray-600">
                  {CATEGORIES[gift.category]}
                  {#if gift.people.length}
                    · für {gift.people.map((p) => p.name).join(', ')}{/if}
                </p>
              </div>
              <div class="flex items-center gap-4">
                <a href={resolve(`/gifts?edit=${gift.id}`)} class="text-sm underline">
                  Bearbeiten<span class="sr-only">: {gift.title}</span>
                </a>
                <button
                  type="button"
                  class="text-sm text-red-800 underline"
                  onclick={() => askDelete(gift)}
                >
                  Löschen<span class="sr-only">: {gift.title}</span>
                </button>
              </div>
            </div>

            <!-- Beschenkungen (F-06) -->
            <section class="mt-5 border-t pt-4" aria-label={`Beschenkungen für ${gift.title}`}>
              <h4 class="font-semibold">Beschenkungen</h4>
              {#if giftings.length}
                <ul class="mt-3 flex flex-col gap-3">
                  {#each giftings as g (g.id)}
                    <li class="rounded border p-3">
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="text-sm">
                          <span class="font-bold"
                            >{g.people.map((p) => p.name).join(', ') ||
                              'Noch keine Empfänger:innen'}</span
                          >
                          {#if g.occasion}<span class="ml-2 text-sm text-gray-600"
                              >{g.occasion.name} {formatDate(g.occasion_date)}</span
                            >{/if}
                          {#if g.given_on}<span class="ml-2 text-sm text-gray-600">
                              verschenkt am {formatDate(g.given_on)}</span
                            >{/if}
                        </span>
                        <span class="ml-auto flex items-center gap-4">
                          <a
                            href={resolve(`/gifts?edit_gifting=${g.id}`)}
                            class="text-sm underline"
                          >
                            Bearbeiten<span class="sr-only">: Beschenkung zu {gift.title}</span>
                          </a>
                          <button
                            type="button"
                            class="text-sm text-red-800 underline"
                            onclick={() => askDeleteGifting(g)}
                          >
                            Löschen<span class="sr-only">: Beschenkung zu {gift.title}</span>
                          </button>
                        </span>
                      </div>

                      <div class="mt-3 flex items-center gap-2">
                        <span
                          class={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm ${STATUS_CLASS[g.status]}`}
                          data-status={g.status}
                        >
                          <span aria-hidden="true">{STATUS[g.status].icon}</span>
                          {STATUS[g.status].label}
                        </span>
                      </div>
                    </li>
                  {/each}
                </ul>
              {:else}
                <p class="mt-2 text-sm text-gray-600">Noch keine Beschenkung.</p>
              {/if}

              <div class="mt-4 flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  class="mt-2 rounded bg-black px-4 py-2 text-white"
                  aria-haspopup="dialog"
                  aria-controls="gifting-form-dialog"
                  onclick={() => openGiftingForm(gift.id)}
                >
                  Beschenkung anlegen
                </button>
              </div>
            </section>
          </li>
        {/each}
      </ul>
    {/if}
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
      action="?/delete"
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

  <dialog
    bind:this={deleteGiftingDialog}
    aria-labelledby="delete-gifting-heading"
    class="m-auto rounded border p-6 backdrop:bg-black/40"
  >
    <h2 id="delete-gifting-heading" class="font-semibold">Beschenkung löschen?</h2>
    <p class="mt-2 text-sm">
      Die Beschenkung zu „{giftingToDelete?.gift.title}“{#if giftingToDelete?.people.length}
        für {giftingToDelete.people.map((person) => person.name).join(', ')}{/if} wird endgültig gelöscht.
      Die Geschenkidee, die Personen und der Anlass bleiben erhalten.
    </p>
    <form
      method="POST"
      action="?/deleteGifting"
      class="mt-4 flex justify-end gap-3"
      use:enhance={() =>
        async ({ update }) => {
          deleteGiftingDialog?.close();
          await update();
        }}
    >
      <input type="hidden" name="id" value={giftingToDelete?.id} />
      <button
        type="button"
        class="rounded border px-4 py-2"
        onclick={() => deleteGiftingDialog?.close()}
      >
        Abbrechen
      </button>
      <button type="submit" class="rounded bg-red-700 px-4 py-2 text-white">Löschen</button>
    </form>
  </dialog>

  {#if data.success}<p role="status" class="mt-4 text-sm text-green-800">{data.success}</p>{/if}
  {#if form?.deleteMessage}
    <p role="alert" class="mt-4 text-sm text-red-800">{form.deleteMessage}</p>
  {/if}

  {#if !isEdit}
    <button
      type="button"
      class="mt-10 rounded bg-black px-4 py-2 text-white"
      aria-haspopup="dialog"
      aria-controls="gift-form-dialog"
      onclick={openForm}
    >
      Geschenkidee hinzufügen
    </button>
  {/if}

  <dialog
    id="gifting-form-dialog"
    bind:this={giftingFormDialog}
    aria-labelledby="gifting-heading"
    class="fixed inset-0 m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
    onclose={() => {
      showGiftingForm = false;
      newGifting = null;
    }}
  >
    <h2 id="gifting-heading" class="text-lg font-semibold">
      {isGiftingEdit ? 'Beschenkung bearbeiten' : 'Beschenkung anlegen'}
    </h2>
    <p class="mt-1 text-sm text-gray-600">Geschenkidee: {giftingTitle}</p>
    {#key [data, newGifting]}
      <form
        method="POST"
        action={isGiftingEdit ? '?/updateGifting' : '?/createGifting'}
        use:enhance={() =>
          async ({ result, update }) => {
            if (result.type === 'redirect') {
              showGiftingForm = false;
              giftingFormDialog?.close();
            }
            fresh = false;
            await update();
          }}
        novalidate
        class="mt-4 flex flex-col gap-3"
      >
        {#if form?.giftingMessage}
          <p role="alert" class="text-sm text-red-800">{form.giftingMessage}</p>
        {/if}
        {#if giftingErrors.gift_id}
          <p role="alert" class="text-sm text-red-800">{giftingErrors.gift_id}</p>
        {/if}
        <input type="hidden" name="gift_id" value={giftingValues.gift_id} />
        {#if isGiftingEdit}<input type="hidden" name="id" value={data.editingGifting?.id} />{/if}

        <label for="status" class="text-sm font-medium">Status</label>
        <select
          id="status"
          name="status"
          bind:value={giftingStatus}
          class="rounded border px-3 py-2"
          aria-invalid={giftingErrors.status ? 'true' : undefined}
          aria-describedby={giftingErrors.status ? 'status-error' : undefined}
        >
          {#each STATUS_ORDER as status (status)}
            <option value={status}>{STATUS[status].label}</option>
          {/each}
        </select>
        {#if giftingErrors.status}
          <p id="status-error" class="text-sm text-red-800">{giftingErrors.status}</p>
        {/if}

        <fieldset
          class="flex flex-col gap-2"
          aria-describedby={giftingErrors.person_ids ? 'person-ids-error' : undefined}
        >
          <legend class="text-sm font-medium">
            Tatsächliche Empfänger:innen{giftingStatus === 'given' ? '' : ' (optional)'}
          </legend>
          {#if data.people.length === 0}
            <p class="text-sm text-gray-600">Noch keine Personen angelegt.</p>
          {:else}
            <div class="max-h-36 overflow-y-auto rounded border p-3">
              {#each data.people as person (person.id)}
                <label class="flex items-center gap-2 py-1 text-sm">
                  <input
                    type="checkbox"
                    name="person_ids"
                    value={person.id}
                    checked={(giftingValues.person_ids ?? []).includes(person.id)}
                  />
                  {person.name}
                </label>
              {/each}
            </div>
          {/if}
          {#if giftingErrors.person_ids}
            <p id="person-ids-error" class="text-sm text-red-800">{giftingErrors.person_ids}</p>
          {/if}
        </fieldset>

        <label for="occasion_id" class="text-sm font-medium">
          Anlass{giftingStatus === 'given' ? '' : ' (optional)'}
        </label>
        <select
          id="occasion_id"
          name="occasion_id"
          required={giftingStatus === 'given'}
          value={giftingValues.occasion_id ?? ''}
          class="rounded border px-3 py-2"
          aria-invalid={giftingErrors.occasion_id ? 'true' : undefined}
          aria-describedby={giftingErrors.occasion_id ? 'occasion-id-error' : undefined}
        >
          <option value="">– bitte wählen –</option>
          {#each data.occasions as occasion (occasion.id)}
            <option value={occasion.id}>{occasion.name}</option>
          {/each}
        </select>
        {#if giftingErrors.occasion_id}
          <p id="occasion-id-error" class="text-sm text-red-800">{giftingErrors.occasion_id}</p>
        {/if}

        <label for="occasion_date" class="text-sm font-medium">
          Anlasstermin{giftingStatus === 'given' ? '' : ' (optional)'}
        </label>
        <input
          id="occasion_date"
          name="occasion_date"
          type="date"
          required={giftingStatus === 'given'}
          value={giftingValues.occasion_date ?? ''}
          class="rounded border px-3 py-2"
          aria-invalid={giftingErrors.occasion_date ? 'true' : undefined}
          aria-describedby={giftingErrors.occasion_date ? 'occasion-date-error' : undefined}
        />
        {#if giftingErrors.occasion_date}
          <p id="occasion-date-error" class="text-sm text-red-800">
            {giftingErrors.occasion_date}
          </p>
        {/if}

        {#if giftingStatus === 'given'}
          <label for="given_on" class="text-sm font-medium">Verschenkdatum</label>
          <input
            id="given_on"
            name="given_on"
            type="date"
            required
            value={giftingValues.given_on ?? today}
            class="rounded border px-3 py-2"
            aria-invalid={giftingErrors.given_on ? 'true' : undefined}
            aria-describedby={giftingErrors.given_on ? 'given-on-error' : undefined}
          />
          {#if giftingErrors.given_on}
            <p id="given-on-error" class="text-sm text-red-800">{giftingErrors.given_on}</p>
          {/if}
        {/if}

        <div class="flex items-center gap-4">
          <button type="submit" class="rounded bg-black px-4 py-2 text-white">
            {isGiftingEdit ? 'Speichern' : 'Anlegen'}
          </button>
          {#if isGiftingEdit}
            <a href={resolve('/gifts')} class="rounded border px-4 py-2">Abbrechen</a>
          {:else}
            <button
              type="button"
              class="rounded border px-4 py-2"
              onclick={() => giftingFormDialog?.close()}
            >
              Abbrechen
            </button>
          {/if}
        </div>
      </form>
    {/key}
  </dialog>

  <dialog
    id="gift-form-dialog"
    bind:this={formDialog}
    aria-labelledby="form-heading"
    class="fixed inset-0 m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
    onclose={() => (showForm = false)}
  >
    <h2 id="form-heading" class="text-lg font-semibold">
      {isEdit ? 'Geschenkidee bearbeiten' : 'Geschenkidee hinzufügen'}
    </h2>
    {#key data}
      <form
        method="POST"
        action={isEdit ? '?/update' : '?/create'}
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
        {#if form?.message && form?.values}
          <p role="alert" class="text-sm text-red-800">{form.message}</p>
        {/if}
        {#if isEdit}<input type="hidden" name="id" value={data.editing?.id} />{/if}

        <label for="title" class="text-sm font-medium">Titel</label>
        <input
          id="title"
          name="title"
          required
          maxlength="200"
          autocomplete="off"
          value={values.title}
          class="rounded border px-3 py-2"
          aria-invalid={errors.title ? 'true' : undefined}
          aria-describedby={errors.title ? 'title-error' : undefined}
        />
        {#if errors.title}<p id="title-error" class="text-sm text-red-800">{errors.title}</p>{/if}

        <label for="description" class="text-sm font-medium">Beschreibung (optional)</label>
        <textarea
          id="description"
          name="description"
          maxlength="2000"
          class="rounded border px-3 py-2"
          aria-invalid={errors.description ? 'true' : undefined}
          aria-describedby={errors.description ? 'description-error' : undefined}
          >{values.description ?? ''}</textarea
        >
        {#if errors.description}
          <p id="description-error" class="text-sm text-red-800">{errors.description}</p>
        {/if}

        <label for="category" class="text-sm font-medium">Kategorie</label>
        <select
          id="category"
          name="category"
          value={values.category}
          class="rounded border px-3 py-2"
        >
          {#each Object.entries(CATEGORIES) as [value, label] (value)}
            <option {value}>{label}</option>
          {/each}
        </select>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="flex flex-col gap-1">
            <label for="price_from" class="text-sm font-medium">Preis von (optional)</label>
            <input
              id="price_from"
              name="price_from"
              inputmode="decimal"
              value={values.price_from ?? ''}
              class="rounded border px-3 py-2"
              aria-invalid={errors.price_from ? 'true' : undefined}
              aria-describedby={errors.price_from ? 'price-from-error' : undefined}
            />
            {#if errors.price_from}
              <p id="price-from-error" class="text-sm text-red-800">{errors.price_from}</p>
            {/if}
          </div>
          <div class="flex flex-col gap-1">
            <label for="price_to" class="text-sm font-medium">Preis bis (optional)</label>
            <input
              id="price_to"
              name="price_to"
              inputmode="decimal"
              value={values.price_to ?? ''}
              class="rounded border px-3 py-2"
              aria-invalid={errors.price_to ? 'true' : undefined}
              aria-describedby={errors.price_to ? 'price-to-error' : undefined}
            />
            {#if errors.price_to}
              <p id="price-to-error" class="text-sm text-red-800">{errors.price_to}</p>
            {/if}
          </div>
        </div>

        <label for="currency" class="text-sm font-medium">Währung (optional)</label>
        <input
          id="currency"
          name="currency"
          maxlength="3"
          placeholder="EUR"
          value={values.currency ?? ''}
          class="rounded border px-3 py-2 uppercase"
          aria-invalid={errors.currency ? 'true' : undefined}
          aria-describedby={errors.currency ? 'currency-error' : undefined}
        />
        {#if errors.currency}
          <p id="currency-error" class="text-sm text-red-800">{errors.currency}</p>
        {/if}

        <fieldset class="flex flex-col gap-2">
          <legend class="text-sm font-medium">Mögliche Empfänger:innen (optional)</legend>
          {#if data.people.length === 0}
            <p class="text-sm text-gray-600">Noch keine Personen angelegt.</p>
          {:else}
            <div class="max-h-32 overflow-y-auto rounded border p-3">
              {#each data.people as person (person.id)}
                <label class="flex items-center gap-2 py-1 text-sm">
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
          {/if}
        </fieldset>

        <fieldset class="flex flex-col gap-2">
          <legend class="text-sm font-medium">Mögliche Anlässe (optional)</legend>
          {#if data.occasions.length === 0}
            <p class="text-sm text-gray-600">Noch keine Anlässe angelegt.</p>
          {:else}
            <div class="max-h-32 overflow-y-auto rounded border p-3">
              {#each data.occasions as occasion (occasion.id)}
                <label class="flex items-center gap-2 py-1 text-sm">
                  <input
                    type="checkbox"
                    name="occasion_ids"
                    value={occasion.id}
                    checked={(values.occasion_ids ?? []).includes(occasion.id)}
                  />
                  {occasion.name}
                </label>
              {/each}
            </div>
          {/if}
        </fieldset>

        <div class="flex items-center gap-4">
          <button type="submit" class="rounded bg-black px-4 py-2 text-white">
            {isEdit ? 'Speichern' : 'Anlegen'}
          </button>
          {#if isEdit}
            <a href={resolve('/gifts')} class="rounded border px-4 py-2">Abbrechen</a>
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
