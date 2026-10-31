<script lang="ts">
  import { enhance } from '$app/forms';
  import type { components } from '$lib/api/schema';
  import { CATEGORIES, formatPrice } from '$lib/display';

  type GiftIn = components['schemas']['GiftIn'];

  let {
    open = $bindable(),
    action,
    editId,
    values,
    errors,
    message,
    people,
    occasions,
    onclose
  }: {
    open: boolean;
    action: '?/create' | '?/update';
    editId: string | null;
    values: GiftIn;
    errors: Partial<Record<keyof GiftIn, string>>;
    message: string | null;
    people: { id: string; name: string }[];
    occasions: { id: string; name: string }[];
    /** Called when the dialog is dismissed (Escape, Abbrechen), not after a successful save. */
    onclose?: () => void;
  } = $props();

  const isEdit = $derived(editId !== null);

  let dialog: HTMLDialogElement | undefined = $state();
  /** True while a successful save redirects, so closing the dialog does not call `onclose`. */
  let saving = false;

  $effect(() => {
    if (open && dialog && !dialog.open) dialog.showModal();
    if (!open && dialog?.open) dialog.close();
  });
</script>

<dialog
  id="gift-form-dialog"
  bind:this={dialog}
  aria-labelledby="gift-form-dialog-heading"
  class="fixed inset-0 m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
  onclose={() => {
    open = false;
    if (!saving) onclose?.();
  }}
>
  <h2 id="gift-form-dialog-heading" class="text-lg font-semibold">
    {isEdit ? 'Geschenkidee bearbeiten' : 'Geschenkidee hinzufügen'}
  </h2>
  <!-- people/occasions are new arrays whenever the page data reloads: re-create the form then,
       but keep it (and its focus) after a failed submit. -->
  {#key [people, occasions]}
    <form
      method="POST"
      {action}
      use:enhance={() =>
        async ({ result, update }) => {
          if (result.type === 'redirect') {
            saving = true;
            open = false;
            dialog?.close();
          }
          await update();
          saving = false;
        }}
      novalidate
      class="mt-4 flex flex-col gap-3"
    >
      {#if message}
        <p role="alert" class="text-sm text-red-800">{message}</p>
      {/if}
      {#if editId}<input type="hidden" name="id" value={editId} />{/if}

      <label for="gift-title" class="text-sm font-medium">Titel</label>
      <input
        id="gift-title"
        name="title"
        required
        maxlength="200"
        autocomplete="off"
        value={values.title}
        class="rounded border px-3 py-2"
        aria-invalid={errors.title ? 'true' : undefined}
        aria-describedby={errors.title ? 'gift-title-error' : undefined}
      />
      {#if errors.title}
        <p id="gift-title-error" class="text-sm text-red-800">{errors.title}</p>
      {/if}

      <label for="gift-description" class="text-sm font-medium">Beschreibung (optional)</label>
      <textarea
        id="gift-description"
        name="description"
        maxlength="2000"
        class="rounded border px-3 py-2"
        aria-invalid={errors.description ? 'true' : undefined}
        aria-describedby={errors.description ? 'gift-description-error' : undefined}
        >{values.description ?? ''}</textarea
      >
      {#if errors.description}
        <p id="gift-description-error" class="text-sm text-red-800">{errors.description}</p>
      {/if}

      <label for="gift-category" class="text-sm font-medium">Kategorie</label>
      <select
        id="gift-category"
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
          <label for="gift-price_from" class="text-sm font-medium">Preis von (optional)</label>
          <input
            id="gift-price_from"
            name="price_from"
            inputmode="decimal"
            value={formatPrice(values.price_from)}
            class="rounded border px-3 py-2"
            aria-invalid={errors.price_from ? 'true' : undefined}
            aria-describedby={errors.price_from ? 'gift-price-from-error' : undefined}
          />
          {#if errors.price_from}
            <p id="gift-price-from-error" class="text-sm text-red-800">{errors.price_from}</p>
          {/if}
        </div>
        <div class="flex flex-col gap-1">
          <label for="gift-price_to" class="text-sm font-medium">Preis bis (optional)</label>
          <input
            id="gift-price_to"
            name="price_to"
            inputmode="decimal"
            value={formatPrice(values.price_to)}
            class="rounded border px-3 py-2"
            aria-invalid={errors.price_to ? 'true' : undefined}
            aria-describedby={errors.price_to ? 'gift-price-to-error' : undefined}
          />
          {#if errors.price_to}
            <p id="gift-price-to-error" class="text-sm text-red-800">{errors.price_to}</p>
          {/if}
        </div>
      </div>

      <label for="gift-currency" class="text-sm font-medium">Währung (optional)</label>
      <input
        id="gift-currency"
        name="currency"
        maxlength="3"
        placeholder="EUR"
        value={values.currency ?? ''}
        class="rounded border px-3 py-2 uppercase"
        aria-invalid={errors.currency ? 'true' : undefined}
        aria-describedby={errors.currency ? 'gift-currency-error' : undefined}
      />
      {#if errors.currency}
        <p id="gift-currency-error" class="text-sm text-red-800">{errors.currency}</p>
      {/if}

      <fieldset class="flex flex-col gap-2">
        <legend class="text-sm font-medium">Mögliche Empfänger:innen (optional)</legend>
        {#if people.length === 0}
          <p class="text-sm text-gray-600">Noch keine Personen angelegt.</p>
        {:else}
          <div class="max-h-32 overflow-y-auto rounded border p-3">
            {#each people as person (person.id)}
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
        {#if occasions.length === 0}
          <p class="text-sm text-gray-600">Noch keine Anlässe angelegt.</p>
        {:else}
          <div class="max-h-32 overflow-y-auto rounded border p-3">
            {#each occasions as occasion (occasion.id)}
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
        <button type="button" class="rounded border px-4 py-2" onclick={() => dialog?.close()}>
          Abbrechen
        </button>
      </div>
    </form>
  {/key}
</dialog>
