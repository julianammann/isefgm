<script lang="ts">
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import {
    CATEGORIES,
    GIFTING_STATUS,
    GIFTING_STATUS_CLASS,
    TASK_STATUS,
    formatDate,
    formatPriceRange
  } from '#lib/display.js';
  import FormDialog from '#lib/components/FormDialog.svelte';
  import Pagination from '#lib/components/Pagination.svelte';
  import PersonFormDialog from '#lib/components/PersonFormDialog.svelte';
  import ShareCreatedDialog from '#lib/components/ShareCreatedDialog.svelte';
  import ShareLinkDialog from '#lib/components/ShareLinkDialog.svelte';
  import { occasionDateLabel } from '#lib/occasion-date.js';
  import { PAGE_SIZE, actionUrl, pageQuery } from '#lib/pagination.js';
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

  type ShareLinkRow = (typeof data.shareLinks)[number];

  /** One opening of the share dialog: a new link (`link: null`) or an edit of `link`. */
  let shareSession = $state.raw<{ seen: ActionData; link: ShareLinkRow | null }>({
    seen: null,
    link: null
  });
  let shareOpen = $state(false);
  /** The failed submit of the open share dialog, if any; a created link is not a failure. */
  const shareFailed = $derived.by(() => {
    if (form === shareSession.seen) return null;
    if (form?.scope === 'share' && !shareSession.link && !form.created) return form;
    if (form?.scope === 'shareEdit' && shareSession.link) return form;
    return null;
  });
  const shareValues = $derived(
    shareFailed?.values ??
      (shareSession.link
        ? {
            person_ids: shareSession.link.people.map((p) => p.id),
            expires_on: shareSession.link.expires_on
          }
        : { person_ids: [person.id], expires_on: null })
  );

  function openShare(link: ShareLinkRow | null) {
    shareSession = { seen: form, link };
    createdSeen = form;
    shareOpen = true;
  }

  /** The action result of the last created link, until its dialog is opened for it. */
  let createdSeen = $state.raw<ActionData>(null);
  let createdOpen = $state(false);
  const createdUrl = $derived(form !== createdSeen ? (form?.created?.url ?? null) : null);
  // The token comes back only with the create result: swap the form for the link dialog.
  $effect(() => {
    if (createdUrl) {
      shareOpen = false;
      createdOpen = true;
    }
  });

  let shareToDelete = $state<ShareLinkRow | null>(null);
  let shareDeleteOpen = $state(false);
  let shareDeleteSeen = $state.raw<ActionData>(null);
  const shareDeleteFailed = $derived(
    shareDeleteOpen && form !== shareDeleteSeen && form?.scope === 'shareDelete' ? form : null
  );

  function askDeleteShare(link: ShareLinkRow) {
    shareToDelete = link;
    shareDeleteSeen = form;
    shareDeleteOpen = true;
  }

  /** Label and colour of a link's state; an expired link may still be marked active. */
  function shareState(link: ShareLinkRow): { label: string; class: string } {
    if (!link.active) return { label: 'Deaktiviert', class: 'border-gray-400 text-gray-700' };
    if (!link.open) return { label: 'Abgelaufen', class: 'border-amber-700 text-amber-800' };
    return { label: 'Aktiv', class: 'border-green-700 text-green-800' };
  }
</script>

<svelte:head><title>{person.name} – Geschenke-Manager</title></svelte:head>

<!-- A list can be empty on a later page only because it is shorter than the longest list. -->
{#snippet none(list: { total: number }, empty: string)}
  <p class="mt-2 text-sm text-gray-600">{list.total > 0 ? 'Keine weiteren Einträge.' : empty}</p>
{/snippet}

<!-- „xx weitere anzeigen“ when this list goes on after this page; jumps to it on the next page. -->
{#snippet more(list: { total: number }, heading: string)}
  {@const remaining = list.total - data.page * PAGE_SIZE}
  {#if remaining > 0}
    <a
      href={resolve(`persons/${person.id}${pageQuery(data.page + 1)}#${heading}`)}
      class="mt-2 inline-block text-sm underline"
    >
      {remaining} weitere anzeigen
    </a>
  {/if}
{/snippet}

{#snippet giftings(list: typeof overview.given, empty: string, heading: string)}
  {#if list.items.length === 0}
    {@render none(list, empty)}
  {:else}
    <ul class="mt-3 flex flex-col gap-3">
      {#each list.items as g (g.id)}
        <li class="rounded border p-3">
          <div class="flex flex-wrap items-center gap-2">
            <a href={resolve(`gifts/${g.gift.id}`)} class="font-semibold underline">
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
  {@render more(list, heading)}
{/snippet}

<!-- Room at the bottom, so the toast never hides the end of the page. -->
<main class="mx-auto max-w-5xl p-8 {data.success ? 'pb-24' : ''}">
  <a href={resolve('persons')} class="text-sm underline">← Alle Personen</a>

  <div class="mt-4 flex flex-wrap items-start justify-between gap-3">
    <h1 class="text-2xl font-bold">{person.name}</h1>
    <div class="flex items-center gap-4">
      <button
        type="button"
        class="text-sm underline"
        aria-haspopup="dialog"
        aria-controls="share-dialog"
        onclick={() => openShare(null)}
      >
        Teilen<span class="sr-only">: Ideen von {person.name}</span>
      </button>
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

  <!-- F-14: read-only links to the ideas of this person, created with „Teilen“ above. -->
  <section class="mt-8" aria-labelledby="share-heading">
    <h2 id="share-heading" class="text-lg font-semibold">
      Geteilte Links ({data.shareLinks.length})
    </h2>
    {#if form?.scope === 'shareToggle'}
      <p role="alert" class="mt-2 text-sm text-red-800">{form.message}</p>
    {/if}
    {#if data.shareLinks.length === 0}
      <p class="mt-2 text-sm text-gray-600">
        Noch nicht geteilt. Mit „Teilen“ entsteht ein Link, über den andere die Ideen ohne Konto
        ansehen können.
      </p>
    {:else}
      <ul class="mt-3 flex flex-col gap-3">
        {#each data.shareLinks as link (link.id)}
          {@const state = shareState(link)}
          {@const names = link.people.map((p) => p.name).join(', ')}
          <li class="rounded border p-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-semibold">{names}</span>
              <span class="rounded-full border px-2 py-0.5 text-sm {state.class}">
                {state.label}
              </span>
            </div>
            <p class="mt-1 text-sm text-gray-600">
              {link.expires_on ? `gültig bis ${formatDate(link.expires_on)}` : 'unbegrenzt gültig'}
              · erstellt am {formatDate(link.created_on)}
            </p>
            <div class="mt-2 flex flex-wrap items-center gap-4">
              <button
                type="button"
                class="text-sm underline"
                aria-haspopup="dialog"
                aria-controls="share-dialog"
                onclick={() => openShare(link)}
              >
                Bearbeiten<span class="sr-only">: Link für {names}</span>
              </button>
              <form method="POST" action={actionUrl('toggleShare', data.page)} use:enhance>
                <input type="hidden" name="id" value={link.id} />
                <input type="hidden" name="active" value={String(!link.active)} />
                <button type="submit" class="text-sm underline">
                  {link.active ? 'Deaktivieren' : 'Aktivieren'}<span class="sr-only"
                    >: Link für {names}</span
                  >
                </button>
              </form>
              <button
                type="button"
                class="text-sm text-red-800 underline"
                aria-haspopup="dialog"
                aria-controls="share-delete"
                onclick={() => askDeleteShare(link)}
              >
                Löschen<span class="sr-only">: Link für {names}</span>
              </button>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <div class="mt-10 grid gap-8">
    <section aria-labelledby="occasions-heading">
      <h2 id="occasions-heading" class="text-lg font-semibold">
        Anlässe ({overview.occasions.total})
      </h2>
      <div class="mt-3 rounded border p-3">
        {#if overview.occasions.items.length === 0}
          {@render none(overview.occasions, 'Keine Anlässe.')}
        {:else}
          <ul class="flex flex-col gap-1">
            {#each overview.occasions.items as occasion (occasion.id)}
              <li>
                {occasion.name}
                <span class="text-sm text-gray-600">
                  {occasionDateLabel(occasion, person.birthday)} · {occasion.recurrence === 'yearly'
                    ? 'Jährlich'
                    : 'Einmalig'}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
        {@render more(overview.occasions, 'occasions-heading')}
      </div>
    </section>
    <section aria-labelledby="ideas-heading">
      <h2 id="ideas-heading" class="text-lg font-semibold">
        Geschenkideen ({overview.ideas.total})
      </h2>
      {#if overview.ideas.items.length === 0}
        {@render none(overview.ideas, 'Keine offenen Geschenkideen.')}
      {:else}
        <ul class="mt-3 flex flex-col gap-3">
          {#each overview.ideas.items as idea (idea.id)}
            {@const price = formatPriceRange(idea)}
            <li class="rounded border p-3">
              <div class="flex flex-wrap items-center gap-2">
                <a href={resolve(`gifts/${idea.id}`)} class="font-semibold underline">
                  {idea.title}
                </a>
                <span class="rounded-full border px-2 py-0.5 text-sm">
                  {CATEGORIES[idea.category]}
                </span>
              </div>
              {#if price || idea.occasions.length}
                <p class="mt-1 text-sm text-gray-600">
                  {price}
                  {#if price && idea.occasions.length}·{/if}
                  {#if idea.occasions.length}für {idea.occasions.map((o) => o.name).join(', ')}{/if}
                </p>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
      {@render more(overview.ideas, 'ideas-heading')}
    </section>
    <section aria-labelledby="planned-heading">
      <h2 id="planned-heading" class="text-lg font-semibold">
        Geplante Beschenkungen ({overview.giftings.total})
      </h2>
      {@render giftings(overview.giftings, 'Keine offenen Beschenkungen.', 'planned-heading')}
    </section>
    <section aria-labelledby="given-heading">
      <h2 id="given-heading" class="text-lg font-semibold">
        Vergangene Geschenke ({overview.given.total})
      </h2>
      {@render giftings(overview.given, 'Noch nichts verschenkt.', 'given-heading')}
    </section>
  </div>

  <Pagination
    page={data.page}
    total={data.total}
    href={(p) => resolve(`persons/${person.id}${pageQuery(p)}`)}
  />

  <!-- Fixed to the screen, so the message shows where the user is. -->
  <div role="status" class="pointer-events-none fixed inset-x-0 bottom-4 flex justify-center px-4">
    {#if data.success}
      <p
        class="max-w-md rounded px-4 py-2 text-sm text-white shadow-lg {data.deleted
          ? 'bg-red-800'
          : 'bg-green-800'}"
      >
        {data.success}
      </p>
    {/if}
  </div>

  <!-- Re-created per opening, so cancelled input is gone; a failed submit keeps the session. -->
  {#key session}
    <PersonFormDialog
      bind:open={editOpen}
      action={actionUrl('update', data.page)}
      editId={person.id}
      {values}
      errors={personForm?.errors ?? {}}
      message={personForm?.message ?? null}
    />
  {/key}

  <FormDialog
    id="person-delete"
    heading="Person löschen?"
    action={actionUrl('delete', data.page)}
    submitLabel="Löschen"
    danger
    bind:open={deleteOpen}
    message={deleteFailed?.message ?? null}
  >
    <p class="text-sm">„{person.name}“ wird mit allen zugehörigen Daten endgültig gelöscht.</p>
  </FormDialog>

  {#key shareSession}
    <ShareLinkDialog
      id="share-dialog"
      heading={shareSession.link ? 'Teilen-Link bearbeiten' : `Ideen von ${person.name} teilen`}
      submitLabel={shareSession.link ? 'Speichern' : 'Link erstellen'}
      action={actionUrl(shareSession.link ? 'updateShare' : 'share', data.page)}
      bind:open={shareOpen}
      people={data.people}
      values={shareValues}
      errors={shareFailed?.errors ?? {}}
      message={shareFailed?.message ?? null}
      linkId={shareSession.link?.id ?? null}
      active={shareSession.link?.active ?? true}
      currentExpiresAt={shareSession.link?.expires_at ?? null}
    />
  {/key}

  <ShareCreatedDialog bind:open={createdOpen} url={createdUrl ?? ''} />

  <FormDialog
    id="share-delete"
    heading="Teilen-Link löschen?"
    action={actionUrl('deleteShare', data.page)}
    submitLabel="Löschen"
    danger
    bind:open={shareDeleteOpen}
    message={shareDeleteFailed?.message ?? null}
  >
    <input type="hidden" name="id" value={shareToDelete?.id} />
    <p class="text-sm">
      Der Link für {shareToDelete?.people.map((p) => p.name).join(', ')} öffnet danach nicht mehr. Das
      lässt sich nicht rückgängig machen; zum vorübergehenden Sperren gibt es „Deaktivieren“.
    </p>
  </FormDialog>
</main>
