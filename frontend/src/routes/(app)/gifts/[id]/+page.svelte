<script lang="ts">
  import { resolve } from '$app/paths';
  import FormDialog from '$lib/components/FormDialog.svelte';
  import GiftFormDialog from '$lib/components/GiftFormDialog.svelte';
  import { CATEGORIES, formatPrice } from '$lib/display';
  import GiftingsSection from './GiftingsSection.svelte';
  import ImagesSection from './ImagesSection.svelte';
  import type { ActionData, PageProps } from './$types';

  let { data, form }: PageProps = $props();

  /**
   * One opening of the edit dialog, holding the action result present at that moment, which
   * belongs to an earlier opening. A new object per opening re-creates the dialog.
   */
  let session = $state.raw<{ seen: ActionData }>({ seen: null });

  const gift = $derived(data.gift);
  const giftForm = $derived(form !== session.seen && form?.scope === 'gift' ? form : null);
  const values = $derived(
    giftForm?.values ?? {
      title: gift.title,
      description: gift.description,
      category: gift.category,
      price_from: gift.price_from,
      price_to: gift.price_to,
      currency: gift.currency,
      person_ids: gift.people.map((p) => p.id),
      occasion_ids: gift.occasions.map((o) => o.id)
    }
  );
  const price = $derived.by(() => {
    const from = formatPrice(gift.price_from);
    const to = formatPrice(gift.price_to);
    const range = from && to ? `${from} – ${to}` : from ? `ab ${from}` : to ? `bis ${to}` : '';
    return range && gift.currency ? `${range} ${gift.currency}` : range;
  });

  let editOpen = $state(false);
  let deleteOpen = $state(false);

  function openEdit() {
    session = { seen: form };
    editOpen = true;
  }

  // A failed delete closes its dialog, so the alert below is not hidden behind it.
  $effect(() => {
    if (form?.scope === 'delete') deleteOpen = false;
  });
</script>

<svelte:head><title>{gift.title} – Geschenke-Manager</title></svelte:head>

<main class="mx-auto max-w-4xl p-8">
  <a href={resolve('/gifts')} class="text-sm underline">← Alle Geschenkideen</a>

  <div class="mt-4 flex flex-wrap items-start justify-between gap-3">
    <h1 class="text-2xl font-bold">{gift.title}</h1>
    <div class="flex items-center gap-4">
      <button
        type="button"
        class="text-sm underline"
        aria-haspopup="dialog"
        aria-controls="gift-form-dialog"
        onclick={openEdit}
      >
        Bearbeiten<span class="sr-only">: {gift.title}</span>
      </button>
      <button
        type="button"
        class="text-sm text-red-800 underline"
        aria-haspopup="dialog"
        aria-controls="gift-delete"
        onclick={() => (deleteOpen = true)}
      >
        Löschen<span class="sr-only">: {gift.title}</span>
      </button>
    </div>
  </div>
  <dl class="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
    <dt class="text-gray-600">Kategorie</dt>
    <dd>{CATEGORIES[gift.category]}</dd>
    {#if price}
      <dt class="text-gray-600">Preisrahmen</dt>
      <dd>{price}</dd>
    {/if}
    {#if gift.people.length}
      <dt class="text-gray-600">Personen</dt>
      <dd>{gift.people.map((p) => p.name).join(', ')}</dd>
    {/if}
    {#if gift.occasions.length}
      <dt class="text-gray-600">Anlässe</dt>
      <dd>{gift.occasions.map((o) => o.name).join(', ')}</dd>
    {/if}
  </dl>
  {#if gift.description}<p class="mt-4 whitespace-pre-line">{gift.description}</p>{/if}

  {#if data.success}<p role="status" class="mt-4 text-sm text-green-800">{data.success}</p>{/if}
  {#if form?.scope === 'delete'}
    <p role="alert" class="mt-4 text-sm text-red-800">{form.message}</p>
  {/if}

  <!-- NotesSection, LinksSection and ImagesSection go here, in this order. -->
  <ImagesSection images={data.images} {form} />

  <GiftingsSection
    gift={data.gift}
    giftings={data.giftings}
    tasksByGifting={data.tasksByGifting}
    people={data.people}
    occasions={data.occasions}
    {form}
  />

  <!-- Re-created per opening, so cancelled input is gone; a failed submit keeps the session. -->
  {#key session}
    <GiftFormDialog
      bind:open={editOpen}
      action="?/update"
      editId={gift.id}
      {values}
      errors={giftForm?.errors ?? {}}
      message={giftForm?.message ?? null}
      people={data.people}
      occasions={data.occasions}
    />
  {/key}

  <FormDialog
    id="gift-delete"
    heading="Geschenkidee löschen?"
    action="?/delete"
    submitLabel="Löschen"
    danger
    bind:open={deleteOpen}
  >
    <p class="text-sm">„{gift.title}“ wird mit allen zugehörigen Daten endgültig gelöscht.</p>
  </FormDialog>
</main>
