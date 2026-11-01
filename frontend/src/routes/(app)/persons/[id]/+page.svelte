<script lang="ts">
  import { resolve } from '$app/paths';
  import {
    CATEGORIES,
    GIFTING_STATUS,
    GIFTING_STATUS_CLASS,
    TASK_STATUS,
    formatDate,
    formatPrice
  } from '$lib/display';
  import FormDialog from '$lib/components/FormDialog.svelte';
  import PersonFormDialog from '$lib/components/PersonFormDialog.svelte';
  import type { ActionData, PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const person = $derived(data.person);
  const overview = $derived(data.overview);

  /**
   * One opening of the edit dialog, holding the action result present at that moment, which
   * belongs to an earlier opening. A new object per opening re-creates the dialog.
   */
  let session = $state.raw<{ seen: ActionData }>({ seen: null });
  let editOpen = $state(false);
  const personForm = $derived(form !== session.seen && form?.scope === 'person' ? form : null);
  const values = $derived(
    personForm?.values ?? {
      name: person.name,
      birthday: person.birthday,
      relationship: person.relationship,
      notes: person.notes
    }
  );

  function openEdit() {
    session = { seen: form };
    editOpen = true;
  }

  let deleteOpen = $state(false);
  /** The action result present when the delete dialog opened, so an older failure stays hidden. */
  let deleteSeen = $state.raw<ActionData>(null);
  // A failed delete keeps its dialog open; only the open delete dialog shows the message.
  const deleteFailed = $derived(
    deleteOpen && form !== deleteSeen && form?.scope === 'delete' ? form : null
  );

  function askDelete() {
    deleteSeen = form;
    deleteOpen = true;
  }

  /** Price range of an idea, e.g. „20,00 – 30,00 EUR“ or „ab 20,00“; empty without a price. */
  function price(idea: (typeof overview.ideas.items)[number]) {
    const from = formatPrice(idea.price_from);
    const to = formatPrice(idea.price_to);
    const range = from && to ? `${from} – ${to}` : from ? `ab ${from}` : to ? `bis ${to}` : '';
    return range && idea.currency ? `${range} ${idea.currency}` : range;
  }

  /** „3 weitere nicht angezeigt“ when a list has more entries than one page. */
  const more = (list: { items: unknown[]; total: number }) =>
    list.total > list.items.length
      ? `${list.total - list.items.length} weitere nicht angezeigt`
      : '';
</script>

<svelte:head><title>{person.name} – Geschenke-Manager</title></svelte:head>

{#snippet giftings(list: typeof overview.given, empty: string)}
  {#if list.items.length === 0}
    <p class="mt-2 text-sm text-gray-600">{empty}</p>
  {:else}
    <ul class="mt-3 flex flex-col gap-3">
      {#each list.items as g (g.id)}
        <li class="rounded border p-3">
          <div class="flex flex-wrap items-center gap-2">
            <a href={resolve(`/gifts/${g.gift.id}`)} class="font-semibold underline">
              {g.gift.title}
            </a>
            <span
              class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm {GIFTING_STATUS_CLASS[
                g.status
              ]}"
            >
              <span aria-hidden="true">{GIFTING_STATUS[g.status].icon}</span>
              {GIFTING_STATUS[g.status].label}
            </span>
          </div>
          <p class="mt-1 text-sm text-gray-600">
            {#if g.occasion}{g.occasion.name} {formatDate(g.occasion_date)}{:else}Ohne Anlass{/if}
            {#if g.given_on}· verschenkt am {formatDate(g.given_on)}{/if}
            {#if g.people.length > 1}· gemeinsam mit {g.people
                .filter((p) => p.id !== person.id)
                .map((p) => p.name)
                .join(', ')}{/if}
          </p>
          {#if g.tasks.length}
            <ul class="mt-2 flex flex-col gap-1 text-sm" aria-label="Aufgaben zu {g.gift.title}">
              {#each g.tasks as t (t.id)}
                <li>
                  <span aria-hidden="true">{TASK_STATUS[t.status].icon}</span>
                  {TASK_STATUS[t.status].label} – {t.title}
                  {#if t.due_on}<span class="text-gray-600">(bis {formatDate(t.due_on)})</span>{/if}
                </li>
              {/each}
            </ul>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
  {#if more(list)}<p class="mt-2 text-sm text-gray-600">{more(list)}</p>{/if}
{/snippet}

<!-- Room at the bottom, so the toast never hides the end of the page. -->
<main class="mx-auto max-w-5xl p-8 {data.success ? 'pb-24' : ''}">
  <a href={resolve('/persons')} class="text-sm underline">← Alle Personen</a>

  <div class="mt-4 flex flex-wrap items-start justify-between gap-3">
    <h1 class="text-2xl font-bold">{person.name}</h1>
    <div class="flex items-center gap-4">
      <button
        type="button"
        class="text-sm underline"
        aria-haspopup="dialog"
        aria-controls="person-form-dialog"
        onclick={openEdit}
      >
        Bearbeiten<span class="sr-only">: {person.name}</span>
      </button>
      <button
        type="button"
        class="text-sm text-red-800 underline"
        aria-haspopup="dialog"
        aria-controls="person-delete"
        onclick={askDelete}
      >
        Löschen<span class="sr-only">: {person.name}</span>
      </button>
    </div>
  </div>
  {#if person.birthday || person.relationship}
    <dl class="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
      {#if person.birthday}
        <dt class="text-gray-600">Geburtstag</dt>
        <dd>{formatDate(person.birthday)}</dd>
      {/if}
      {#if person.relationship}
        <dt class="text-gray-600">Beziehung</dt>
        <dd>{person.relationship}</dd>
      {/if}
    </dl>
  {/if}
  {#if person.notes}<p class="mt-4 whitespace-pre-line">{person.notes}</p>{/if}

  <div class="mt-10 grid gap-8">
    <section aria-labelledby="occasions-heading">
      <h2 id="occasions-heading" class="text-lg font-semibold">
        Anlässe ({overview.occasions.total})
      </h2>
      <div class="mt-3 rounded border p-3">
        {#if overview.occasions.items.length === 0}
          <p class="mt-2 text-sm text-gray-600">Keine Anlässe.</p>
        {:else}
          <ul class="flex flex-col gap-1">
            {#each overview.occasions.items as occasion (occasion.id)}
              <li>
                {occasion.name}
                {#if occasion.date}
                  <span class="text-sm text-gray-600">
                    {formatDate(occasion.date)}{occasion.recurrence === 'yearly'
                      ? ' · jährlich'
                      : ''}
                  </span>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}
        {#if more(overview.occasions)}
          <p class="mt-2 text-sm text-gray-600">{more(overview.occasions)}</p>
        {/if}
      </div>
    </section>
    <section aria-labelledby="ideas-heading">
      <h2 id="ideas-heading" class="text-lg font-semibold">
        Geschenkideen ({overview.ideas.total})
      </h2>
      {#if overview.ideas.items.length === 0}
        <p class="mt-2 text-sm text-gray-600">Keine offenen Geschenkideen.</p>
      {:else}
        <ul class="mt-3 flex flex-col gap-3">
          {#each overview.ideas.items as idea (idea.id)}
            <li class="rounded border p-3">
              <div class="flex flex-wrap items-center gap-2">
                <a href={resolve(`/gifts/${idea.id}`)} class="font-semibold underline">
                  {idea.title}
                </a>
                <span class="rounded-full border px-2 py-0.5 text-sm">
                  {CATEGORIES[idea.category]}
                </span>
              </div>
              {#if price(idea) || idea.occasions.length}
                <p class="mt-1 text-sm text-gray-600">
                  {price(idea)}
                  {#if price(idea) && idea.occasions.length}·{/if}
                  {#if idea.occasions.length}für {idea.occasions.map((o) => o.name).join(', ')}{/if}
                </p>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
      {#if more(overview.ideas)}
        <p class="mt-2 text-sm text-gray-600">{more(overview.ideas)}</p>
      {/if}
    </section>
    <section aria-labelledby="planned-heading">
      <h2 id="planned-heading" class="text-lg font-semibold">
        Geplante Beschenkungen ({overview.giftings.total})
      </h2>
      {@render giftings(overview.giftings, 'Keine offenen Beschenkungen.')}
    </section>
    <section aria-labelledby="given-heading">
      <h2 id="given-heading" class="text-lg font-semibold">
        Vergangene Geschenke ({overview.given.total})
      </h2>
      {@render giftings(overview.given, 'Noch nichts verschenkt.')}
    </section>
  </div>

  <!-- Fixed to the screen, so the message shows where the user is. -->
  <div role="status" class="pointer-events-none fixed inset-x-0 bottom-4 flex justify-center px-4">
    {#if data.success}
      <p class="max-w-md rounded bg-green-800 px-4 py-2 text-sm text-white shadow-lg">
        {data.success}
      </p>
    {/if}
  </div>

  <!-- Re-created per opening, so cancelled input is gone; a failed submit keeps the session. -->
  {#key session}
    <PersonFormDialog
      bind:open={editOpen}
      action="?/update"
      editId={person.id}
      {values}
      errors={personForm?.errors ?? {}}
      message={personForm?.message ?? null}
    />
  {/key}

  <FormDialog
    id="person-delete"
    heading="Person löschen?"
    action="?/delete"
    submitLabel="Löschen"
    danger
    bind:open={deleteOpen}
    message={deleteFailed?.message ?? null}
  >
    <p class="text-sm">„{person.name}“ wird mit allen zugehörigen Daten endgültig gelöscht.</p>
  </FormDialog>
</main>
