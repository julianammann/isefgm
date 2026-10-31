<script lang="ts">
  import FormDialog from '$lib/components/FormDialog.svelte';
  import type { ActionData, PageData } from './$types';

  type Note = PageData['notes'][number];

  let { notes, form }: Pick<PageData, 'notes'> & { form: ActionData } = $props();

  let formOpen = $state(false);
  let deleteOpen = $state(false);
  let toDelete = $state.raw<Note | null>(null);
  /** The action result present when the delete dialog opened, so an older failure stays hidden. */
  let deleteSeen = $state.raw<ActionData>(null);
  /** One opening of the form dialog: the note to edit (null for a new one) and the earlier action result. */
  let session = $state.raw<{ note: Note | null; seen: ActionData }>({ note: null, seen: null });

  // A failed delete keeps its dialog open; only the open delete dialog shows the message.
  const deleteFailed = $derived(
    deleteOpen && form !== deleteSeen && form?.scope === 'delete' ? form : null
  );
  const failed = $derived(form !== session.seen && form?.scope === 'note' ? form : null);
  const values = $derived(
    failed?.values ?? { label: session.note?.label ?? '', text: session.note?.text ?? '' }
  );
  const errors = $derived(failed?.errors ?? {});

  function openForm(note: Note | null) {
    session = { note, seen: form };
    formOpen = true;
  }

  function askDelete(note: Note) {
    toDelete = note;
    deleteSeen = form;
    deleteOpen = true;
  }
</script>

<section class="mt-10" aria-labelledby="notes-heading">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <h2 id="notes-heading" class="text-lg font-semibold">Notizen</h2>
    <button
      type="button"
      class="rounded bg-black px-4 py-2 text-white"
      aria-haspopup="dialog"
      aria-controls="note-form"
      onclick={() => openForm(null)}
    >
      + Notiz
    </button>
  </div>

  {#if notes.length}
    <ul class="mt-4 flex flex-col gap-3">
      {#each notes as n (n.id)}
        <li class="rounded border p-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-bold">{n.label}</span>
            <span class="ml-auto flex items-center gap-4">
              <button
                type="button"
                class="text-sm underline"
                aria-haspopup="dialog"
                aria-controls="note-form"
                onclick={() => openForm(n)}
              >
                Bearbeiten<span class="sr-only">: Notiz {n.label}</span>
              </button>
              <button
                type="button"
                class="text-sm text-red-800 underline"
                aria-haspopup="dialog"
                aria-controls="note-delete"
                onclick={() => askDelete(n)}
              >
                Löschen<span class="sr-only">: Notiz {n.label}</span>
              </button>
            </span>
          </div>
          <p class="mt-2 text-sm whitespace-pre-line">{n.text}</p>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mt-2 text-sm text-gray-600">Noch keine Notizen.</p>
  {/if}
</section>

<FormDialog
  id="note-form"
  heading={session.note ? 'Notiz bearbeiten' : 'Notiz anlegen'}
  action={session.note ? '?/updateNote' : '?/createNote'}
  submitLabel={session.note ? 'Speichern' : 'Anlegen'}
  bind:open={formOpen}
  message={failed?.message ?? null}
>
  {#key session}
    {#if session.note}<input type="hidden" name="id" value={session.note.id} />{/if}

    <label for="note-label" class="text-sm font-medium">Bezeichnung</label>
    <input
      id="note-label"
      name="label"
      type="text"
      value={values.label}
      class="rounded border px-3 py-2"
      aria-invalid={errors.label ? 'true' : undefined}
      aria-describedby={errors.label ? 'note-label-error' : undefined}
    />
    {#if errors.label}<p id="note-label-error" class="text-sm text-red-800">{errors.label}</p>{/if}

    <label for="note-text" class="text-sm font-medium">Text</label>
    <textarea
      id="note-text"
      name="text"
      rows="5"
      class="rounded border px-3 py-2"
      aria-invalid={errors.text ? 'true' : undefined}
      aria-describedby={errors.text ? 'note-text-error' : undefined}>{values.text}</textarea
    >
    {#if errors.text}<p id="note-text-error" class="text-sm text-red-800">{errors.text}</p>{/if}
  {/key}
</FormDialog>

<FormDialog
  id="note-delete"
  heading="Notiz löschen?"
  action="?/deleteNote"
  submitLabel="Löschen"
  danger
  bind:open={deleteOpen}
  message={deleteFailed?.message ?? null}
>
  <input type="hidden" name="id" value={toDelete?.id} />
  <p class="text-sm">„{toDelete?.label}“ wird endgültig gelöscht.</p>
</FormDialog>
