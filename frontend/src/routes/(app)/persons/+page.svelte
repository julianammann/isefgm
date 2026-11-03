<script lang="ts">
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import Pagination from '#lib/components/Pagination.svelte';
  import PersonFormDialog from '#lib/components/PersonFormDialog.svelte';
  import ShareCreatedDialog from '#lib/components/ShareCreatedDialog.svelte';
  import ShareLinkDialog from '#lib/components/ShareLinkDialog.svelte';
  import { formatDate } from '#lib/display.js';
  import { actionUrl, pageQuery } from '#lib/pagination.js';
  import type { ActionData, PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const isEdit = $derived(data.editing !== null);
  /**
   * One opening of the form dialog, holding the action result present at that moment, which
   * belongs to an earlier opening. A new object per opening re-creates the dialog.
   */
  let session = $state.raw<{ seen: ActionData }>({ seen: null });
  // Share results carry a scope; person results do not.
  const personForm = $derived(
    form !== session.seen && form?.values && form.scope === undefined ? form : null
  );
  const values = $derived(
    personForm?.values ??
      data.editing ?? { name: '', birthday: null, relationship: null, notes: null }
  );
  const errors = $derived(personForm?.errors ?? {});

  let showForm = $state(false);
  let previousEditId = $state<string | null>(null);
  let dialog: HTMLDialogElement | null = null;
  let toDelete = $state<{ id: string; name: string } | null>(null);

  /** Drops `?edit` when the edit dialog is closed with Escape or Abbrechen. */
  function leaveEdit() {
    if (page.url.searchParams.has('edit')) {
      goto(resolve(`persons${pageQuery(data.page)}`), { replace: true, reset: false });
    }
  }

  $effect(() => {
    const editId = data.editing?.id ?? null;
    if (previousEditId && !editId) showForm = false;
    if (editId && editId !== previousEditId) openForm();
    previousEditId = editId;
  });

  function openForm() {
    session = { seen: form };
    showForm = true;
  }

  function askDelete(person: { id: string; name: string }) {
    toDelete = person;
    dialog?.showModal();
  }

  /** One opening of the share dialog, started from the row of `person`. */
  let shareSession = $state.raw<{ seen: ActionData; person: { id: string; name: string } }>({
    seen: null,
    person: { id: '', name: '' }
  });
  let shareOpen = $state(false);
  const shareFailed = $derived(
    form !== shareSession.seen && form?.scope === 'share' && !form.created ? form : null
  );

  function openShare(person: { id: string; name: string }) {
    shareSession = { seen: form, person };
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
</script>

<svelte:head
  ><title
    >{data.page > 1
      ? `Personen – Seite ${data.page} – Geschenke-Manager`
      : 'Personen – Geschenke-Manager'}</title
  ></svelte:head
>

<!-- Room at the bottom, so the toast never hides the end of the page. -->
<main class="mx-auto max-w-4xl p-8 {data.success ? 'pb-24' : ''}">
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
                  <a href={resolve(`persons/${person.id}`)} class="font-bold underline"
                    >{person.name}</a
                  >
                </h3>
                {#if person.birthday || person.relationship}
                  <p class="mt-1 text-sm text-gray-600">
                    {#if person.birthday}Geb. {formatDate(person.birthday)}{/if}
                    {#if person.birthday && person.relationship}·{/if}
                    {#if person.relationship}{person.relationship}{/if}
                  </p>
                {/if}
              </div>
              <div class="flex items-center gap-4">
                <button
                  type="button"
                  class="text-sm underline"
                  aria-haspopup="dialog"
                  aria-controls="share-dialog"
                  onclick={() => openShare(person)}
                >
                  Teilen<span class="sr-only">: Ideen von {person.name}</span>
                </button>
                <a
                  href={resolve(`persons${pageQuery(data.page, { edit: person.id })}`)}
                  class="text-sm underline"
                  >Bearbeiten<span class="sr-only">: {person.name}</span>
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
      href={(p) => resolve(`persons${pageQuery(p)}`)}
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
      bind:open={showForm}
      action={actionUrl(isEdit ? 'update' : 'create', data.page)}
      editId={data.editing?.id ?? null}
      {values}
      {errors}
      message={personForm?.message ?? null}
      keepPosition={false}
      onclose={leaveEdit}
    />
  {/key}

  {#key shareSession}
    <ShareLinkDialog
      id="share-dialog"
      heading="Ideen von {shareSession.person.name} teilen"
      submitLabel="Link erstellen"
      action={actionUrl('share', data.page)}
      bind:open={shareOpen}
      people={data.people}
      values={shareFailed?.values ?? { person_ids: [shareSession.person.id], expires_on: null }}
      errors={shareFailed?.errors ?? {}}
      message={shareFailed?.message ?? null}
    />
  {/key}

  <ShareCreatedDialog bind:open={createdOpen} url={createdUrl ?? ''} />
</main>
