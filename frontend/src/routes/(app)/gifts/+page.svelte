<script lang="ts">
  import { enhance } from '$app/forms';
  import { onMount } from 'svelte';

  let { data, form } = $props();
  let titleInput: HTMLInputElement | undefined = $state();
  let createDialog: HTMLDialogElement | undefined = $state();
  let giftingDialog: HTMLDialogElement | undefined = $state();
  let deleteGiftingDialog: HTMLDialogElement | undefined = $state();
  let giftingToDelete: Gifting | null = $state(null);
  type Gifting = (typeof data.giftingsByGift)[string][number];
  let giftingForm: {
    key: number;
    giftId: string;
    giftTitle: string;
    gifting: Gifting | null;
    defaultPersonIds: string[];
  } | null = $state(null);
  let giftingStatus = $state<Status>('idea');
  let giftingFormKey = 0;

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
  const msg = (action: string, id: string | null) =>
    form?.action === action && form?.id === id ? form?.message : undefined;
  const saved = (action: string, id: string) =>
    form?.action === action && form?.id === id && form?.saved === true;

  function confirmDelete(cancel: () => void, description: string) {
    if (
      !window.confirm(
        `${description} endgültig löschen? Dies kann nicht rückgängig gemacht werden.`
      )
    ) {
      cancel();
    }
  }

  function openCreateDialog() {
    createDialog?.showModal();
  }

  function openGiftingDialog(
    giftId: string,
    giftTitle: string,
    gifting: Gifting | null = null,
    initialStatus: Status = 'idea'
  ) {
    giftingFormKey += 1;
    const gift = data.gifts.find((item) => item.id === giftId);
    giftingForm = {
      key: giftingFormKey,
      giftId,
      giftTitle,
      gifting,
      defaultPersonIds: gift?.people.map((person) => person.id) ?? []
    };
    giftingStatus = gifting?.status ?? initialStatus;
    giftingDialog?.showModal();
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
      <ul class="mt-4 divide-y rounded border">
        {#each data.gifts as gift (gift.id)}
          {@const giftings = data.giftingsByGift[gift.id] ?? []}
          <li class="p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 class="text-lg font-semibold">{gift.title}</h3>
                <p class="mt-1 text-sm text-gray-600">
                  {CATEGORIES[gift.category]}
                  {#if gift.people.length}
                    · für {gift.people.map((p) => p.name).join(', ')}{/if}
                </p>
              </div>
              <details>
                <summary class="cursor-pointer text-sm underline">Idee bearbeiten</summary>

                <form
                  method="POST"
                  action="?/update"
                  class="mt-4 flex flex-col gap-3"
                  use:enhance={() =>
                    async ({ update }) => {
                      await update({ reset: false, invalidateAll: true });
                    }}
                >
                  <input type="hidden" name="id" value={gift.id} />
                  <label class="flex flex-col gap-1 text-sm font-medium">
                    Titel
                    <input
                      name="title"
                      required
                      maxlength="200"
                      value={gift.title}
                      class="rounded border px-3 py-2 font-normal"
                    />
                  </label>
                  <label class="flex flex-col gap-1 text-sm font-medium">
                    Beschreibung
                    <textarea
                      name="description"
                      maxlength="2000"
                      class="rounded border px-3 py-2 font-normal"
                      >{gift.description ?? ''}</textarea
                    >
                  </label>
                  <label class="flex flex-col gap-1 text-sm font-medium">
                    Kategorie
                    <select name="category" class="rounded border px-3 py-2 font-normal">
                      {#each Object.entries(CATEGORIES) as [value, label] (value)}
                        <option {value} selected={value === gift.category}>{label}</option>
                      {/each}
                    </select>
                  </label>
                  <div class="grid gap-3 sm:grid-cols-2">
                    <label class="flex flex-col gap-1 text-sm font-medium">
                      Preis von
                      <input
                        name="price_from"
                        inputmode="decimal"
                        value={gift.price_from ?? ''}
                        class="rounded border px-3 py-2 font-normal"
                      />
                    </label>
                    <label class="flex flex-col gap-1 text-sm font-medium">
                      Preis bis
                      <input
                        name="price_to"
                        inputmode="decimal"
                        value={gift.price_to ?? ''}
                        class="rounded border px-3 py-2 font-normal"
                      />
                    </label>
                  </div>
                  <input type="hidden" name="currency" value={gift.currency ?? ''} />
                  <fieldset class="flex flex-col gap-2">
                    <legend class="text-sm font-medium">Mögliche Empfänger:innen</legend>
                    <div class="max-h-32 overflow-y-auto rounded border p-3">
                      {#each data.people as p (p.id)}
                        <label class="flex items-center gap-2 py-1 text-sm">
                          <input
                            type="checkbox"
                            name="person_ids"
                            value={p.id}
                            checked={gift.people.some((x) => x.id === p.id)}
                          />
                          {p.name}
                        </label>
                      {/each}
                    </div>
                  </fieldset>
                  <fieldset class="flex flex-col gap-2">
                    <legend class="text-sm font-medium">Mögliche Anlässe</legend>
                    <div class="max-h-32 overflow-y-auto rounded border p-3">
                      {#each data.occasions as o (o.id)}
                        <label class="flex items-center gap-2 py-1 text-sm">
                          <input
                            type="checkbox"
                            name="occasion_ids"
                            value={o.id}
                            checked={gift.occasions.some((x) => x.id === o.id)}
                          />
                          {o.name}
                        </label>
                      {/each}
                    </div>
                  </fieldset>
                  <button type="submit" class="self-start rounded bg-black px-4 py-2 text-white">
                    Speichern
                  </button>
                  {#if saved('update', gift.id)}
                    <p role="status" class="text-sm text-green-800">Änderungen gespeichert.</p>
                  {/if}
                  {#if msg('update', gift.id)}
                    <p role="alert" class="text-sm text-red-800">{msg('update', gift.id)}</p>
                  {/if}
                </form>
                <form
                  method="POST"
                  action="?/delete"
                  class="mt-3 border-t pt-3"
                  use:enhance={({ cancel }) =>
                    confirmDelete(cancel, `Die Geschenkidee „${gift.title}“`)}
                >
                  <input type="hidden" name="id" value={gift.id} />
                  <button type="submit" class="text-sm text-red-800 underline">Idee löschen</button>
                  {#if msg('delete', gift.id)}
                    <p role="alert" class="text-sm text-red-800">{msg('delete', gift.id)}</p>
                  {/if}
                </form>
              </details>
            </div>

            <!-- Beschenkungen (F-06) -->
            <section class="mt-5 border-t pt-4" aria-label={`Beschenkungen für ${gift.title}`}>
              <h4 class="font-semibold">Beschenkungen</h4>
              {#if giftings.length}
                <ul class="mt-3 flex flex-col gap-3">
                  {#each giftings as g (g.id)}
                    <li class="rounded border p-3">
                      <div class="flex flex-wrap items-center gap-2">
                        <span
                          class={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm ${STATUS_CLASS[g.status]}`}
                          data-status={g.status}
                        >
                          <span aria-hidden="true">{STATUS[g.status].icon}</span>
                          {STATUS[g.status].label}
                        </span>
                        <span class="text-sm">
                          {g.people.map((p) => p.name).join(', ') || 'Noch keine Empfänger:innen'}
                          {#if g.occasion}
                            · {g.occasion.name} {formatDate(g.occasion_date)}{/if}
                          {#if g.given_on}
                            · verschenkt am {formatDate(g.given_on)}{/if}
                        </span>
                      </div>

                      <div class="mt-3 flex flex-wrap items-center gap-3">
                        <button
                          type="button"
                          class="rounded border px-3 py-2 text-sm"
                          aria-haspopup="dialog"
                          aria-controls="gifting-dialog"
                          onclick={() => openGiftingDialog(gift.id, gift.title, g)}
                        >
                          Beschenkung bearbeiten
                        </button>
                        <button
                          type="button"
                          class="text-sm text-red-800 underline"
                          aria-haspopup="dialog"
                          aria-controls="delete-gifting-dialog"
                          onclick={() => askDeleteGifting(g)}
                        >
                          Beschenkung löschen
                        </button>
                      </div>
                      {#if form?.id === g.id && form?.message}
                        <p role="alert" class="mt-2 text-sm text-red-800">{form.message}</p>
                      {/if}
                    </li>
                  {/each}
                </ul>
              {:else}
                <p class="mt-2 text-sm text-gray-600">Noch keine Beschenkung.</p>
              {/if}

              <div class="mt-4 flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  class="rounded border px-3 py-2 text-sm"
                  aria-haspopup="dialog"
                  aria-controls="gifting-dialog"
                  onclick={() => openGiftingDialog(gift.id, gift.title)}
                >
                  Beschenkung anlegen
                </button>
                <button
                  type="button"
                  class="text-sm underline"
                  aria-haspopup="dialog"
                  aria-controls="gifting-dialog"
                  onclick={() => openGiftingDialog(gift.id, gift.title, null, 'given')}
                >
                  Vergangenes Geschenk nachtragen …
                </button>
              </div>
            </section>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <dialog
    id="delete-gifting-dialog"
    bind:this={deleteGiftingDialog}
    aria-labelledby="delete-gifting-heading"
    class="m-auto w-[calc(100%-2rem)] max-w-lg rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
  >
    <h2 id="delete-gifting-heading" class="font-semibold">Beschenkung löschen?</h2>
    <p class="mt-2 text-sm">
      Möchtest du die Beschenkung für
      <span class="font-medium"
        >{giftingToDelete?.people.map((person) => person.name).join(', ') ||
          'die ausgewählten Empfänger:innen'}</span
      >
      zu „{giftingToDelete?.gift.title}“ endgültig löschen? Dies kann nicht rückgängig gemacht
      werden.
    </p>
    <form
      method="POST"
      action="?/deleteGifting"
      class="mt-4 flex justify-end gap-3"
      use:enhance={() =>
        async ({ result, update }) => {
          if (result.type === 'success') deleteGiftingDialog?.close();
          await update();
        }}
    >
      <input type="hidden" name="gifting_id" value={giftingToDelete?.id} />
      {#if form?.action === 'deleteGifting' && form.id === giftingToDelete?.id && form.message}
        <p role="alert" class="mr-auto self-center text-sm text-red-800">{form.message}</p>
      {/if}
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

  <button
    type="button"
    class="mt-10 rounded bg-black px-4 py-2 text-white"
    aria-haspopup="dialog"
    aria-controls="gift-create-dialog"
    onclick={openCreateDialog}
  >
    Geschenkidee hinzufügen
  </button>

  <dialog
    id="gifting-dialog"
    bind:this={giftingDialog}
    aria-labelledby="gifting-heading"
    class="fixed inset-0 m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
    onclose={() => (giftingForm = null)}
  >
    {#if giftingForm}
      {#key giftingForm.key}
        <h2 id="gifting-heading" class="text-lg font-semibold">
          {giftingForm.gifting ? 'Beschenkung bearbeiten' : 'Beschenkung anlegen'}
        </h2>
        <p class="mt-1 text-sm text-gray-600">Geschenkidee: {giftingForm.giftTitle}</p>
        <form
          method="POST"
          action="?/saveGifting"
          class="mt-4 flex flex-col gap-3"
          use:enhance={() =>
            async ({ result, update }) => {
              await update({ reset: false, invalidateAll: true });
              if (result.type === 'success') giftingDialog?.close();
            }}
        >
          <input type="hidden" name="gift_id" value={giftingForm.giftId} />
          {#if giftingForm.gifting}
            <input type="hidden" name="gifting_id" value={giftingForm.gifting.id} />
          {/if}

          <label class="flex flex-col gap-1 text-sm font-medium">
            Status
            <select
              name="status"
              bind:value={giftingStatus}
              class="rounded border px-3 py-2 font-normal"
            >
              {#each STATUS_ORDER as status (status)}
                <option value={status}>{STATUS[status].label}</option>
              {/each}
            </select>
          </label>

          <fieldset class="flex flex-col gap-2">
            <legend class="text-sm font-medium">Tatsächliche Empfänger:innen</legend>
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
                      checked={giftingForm.gifting
                        ? giftingForm.gifting.people.some((selected) => selected.id === person.id)
                        : giftingForm.defaultPersonIds.includes(person.id)}
                    />
                    {person.name}
                  </label>
                {/each}
              </div>
            {/if}
          </fieldset>

          <label class="flex flex-col gap-1 text-sm font-medium">
            Anlass
            <select
              name="occasion_id"
              required={giftingStatus === 'given'}
              class="rounded border px-3 py-2 font-normal"
            >
              <option value="">– bitte wählen –</option>
              {#each data.occasions as occasion (occasion.id)}
                <option
                  value={occasion.id}
                  selected={occasion.id === giftingForm.gifting?.occasion?.id}
                >
                  {occasion.name}
                </option>
              {/each}
            </select>
          </label>
          <label class="flex flex-col gap-1 text-sm font-medium">
            Anlasstermin
            <input
              type="date"
              name="occasion_date"
              required={giftingStatus === 'given'}
              value={giftingForm.gifting?.occasion_date ?? ''}
              class="rounded border px-3 py-2 font-normal"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm font-medium">
            Verschenkdatum
            <input
              type="date"
              name="given_on"
              required={giftingStatus === 'given'}
              value={giftingForm.gifting?.given_on ?? today}
              class="rounded border px-3 py-2 font-normal"
            />
          </label>

          {#if form?.action === 'saveGifting' && form.id === (giftingForm.gifting?.id ?? giftingForm.giftId) && form.message}
            <p role="alert" class="text-sm text-red-800">{form.message}</p>
          {/if}
          <div class="flex items-center justify-end gap-3">
            <button
              type="button"
              class="rounded border px-4 py-2"
              onclick={() => giftingDialog?.close()}
            >
              Abbrechen
            </button>
            <button type="submit" class="rounded bg-black px-4 py-2 text-white"> Speichern </button>
          </div>
        </form>
      {/key}
    {/if}
  </dialog>

  <dialog
    id="gift-create-dialog"
    bind:this={createDialog}
    aria-labelledby="gift-create-heading"
    class="fixed inset-0 m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
  >
    <h2 id="gift-create-heading" class="text-lg font-semibold">Geschenkidee hinzufügen</h2>
    <p class="mt-1 text-sm text-gray-600">
      Du kannst die Geschenkidee direkt vollständig erfassen.
    </p>
    <form
      method="POST"
      action="?/create"
      class="mt-4 flex flex-col gap-3"
      use:enhance={() =>
        async ({ result, update }) => {
          await update({ reset: result.type === 'success', invalidateAll: true });
          if (result.type === 'success') {
            createDialog?.close();
          } else {
            titleInput?.focus();
          }
        }}
    >
      <label for="new-title" class="flex flex-col gap-1 text-sm font-medium">
        Titel
        <input
          id="new-title"
          name="title"
          required
          maxlength="200"
          autocomplete="off"
          bind:this={titleInput}
          class="rounded border px-3 py-2 font-normal"
        />
      </label>
      <label for="new-description" class="flex flex-col gap-1 text-sm font-medium">
        Beschreibung
        <textarea
          id="new-description"
          name="description"
          maxlength="2000"
          class="rounded border px-3 py-2 font-normal"></textarea>
      </label>
      <label for="new-category" class="flex flex-col gap-1 text-sm font-medium">
        Kategorie
        <select id="new-category" name="category" class="rounded border px-3 py-2 font-normal">
          {#each Object.entries(CATEGORIES) as [value, label] (value)}
            <option {value} selected={value === 'other'}>{label}</option>
          {/each}
        </select>
      </label>
      <div class="grid gap-3 sm:grid-cols-2">
        <label for="new-price-from" class="flex flex-col gap-1 text-sm font-medium">
          Preis von
          <input
            id="new-price-from"
            name="price_from"
            inputmode="decimal"
            class="rounded border px-3 py-2 font-normal"
          />
        </label>
        <label for="new-price-to" class="flex flex-col gap-1 text-sm font-medium">
          Preis bis
          <input
            id="new-price-to"
            name="price_to"
            inputmode="decimal"
            class="rounded border px-3 py-2 font-normal"
          />
        </label>
      </div>
      <label for="new-currency" class="flex flex-col gap-1 text-sm font-medium">
        Währung (optional)
        <input
          id="new-currency"
          name="currency"
          maxlength="3"
          pattern="[A-Za-z]{3}"
          placeholder="EUR"
          class="rounded border px-3 py-2 font-normal uppercase"
        />
      </label>
      <fieldset class="flex flex-col gap-2">
        <legend class="text-sm font-medium">Mögliche Empfänger:innen</legend>
        {#if data.people.length === 0}
          <p class="text-sm text-gray-600">Noch keine Personen angelegt.</p>
        {:else}
          <div class="max-h-32 overflow-y-auto rounded border p-3">
            {#each data.people as person (person.id)}
              <label class="flex items-center gap-2 py-1 text-sm">
                <input type="checkbox" name="person_ids" value={person.id} />
                {person.name}
              </label>
            {/each}
          </div>
        {/if}
      </fieldset>
      <fieldset class="flex flex-col gap-2">
        <legend class="text-sm font-medium">Mögliche Anlässe</legend>
        {#if data.occasions.length === 0}
          <p class="text-sm text-gray-600">Noch keine Anlässe angelegt.</p>
        {:else}
          <div class="max-h-32 overflow-y-auto rounded border p-3">
            {#each data.occasions as occasion (occasion.id)}
              <label class="flex items-center gap-2 py-1 text-sm">
                <input type="checkbox" name="occasion_ids" value={occasion.id} />
                {occasion.name}
              </label>
            {/each}
          </div>
        {/if}
      </fieldset>
      {#if msg('create', null)}<p role="alert" class="text-sm text-red-800">
          {msg('create', null)}
        </p>{/if}
      <div class="flex items-center justify-end gap-3">
        <button
          type="button"
          class="rounded border px-4 py-2"
          onclick={() => createDialog?.close()}
        >
          Abbrechen
        </button>
        <button type="submit" class="rounded bg-black px-4 py-2 text-white">Anlegen</button>
      </div>
    </form>
  </dialog>
</main>
