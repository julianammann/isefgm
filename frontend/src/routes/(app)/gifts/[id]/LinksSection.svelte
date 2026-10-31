<script lang="ts">
  import FormDialog from '$lib/components/FormDialog.svelte';
  import type { ActionData, PageData } from './$types';

  type Link = PageData['links'][number];

  let { links, form }: Pick<PageData, 'links'> & { form: ActionData } = $props();

  let formOpen = $state(false);
  let deleteOpen = $state(false);
  let toDelete = $state.raw<Link | null>(null);
  /** The action result present when the delete dialog opened, so an older failure stays hidden. */
  let deleteSeen = $state.raw<ActionData>(null);
  /** One opening of the form dialog: the link to edit (null for a new one) and the earlier action result. */
  let session = $state.raw<{ link: Link | null; seen: ActionData }>({ link: null, seen: null });

  // A failed delete keeps its dialog open; only the open delete dialog shows the message.
  const deleteFailed = $derived(
    deleteOpen && form !== deleteSeen && form?.scope === 'delete' ? form : null
  );
  const failed = $derived(form !== session.seen && form?.scope === 'link' ? form : null);
  const values = $derived(
    failed?.values ?? { label: session.link?.label ?? '', url: session.link?.url ?? '' }
  );
  const errors = $derived(failed?.errors ?? {});

  function openForm(link: Link | null) {
    session = { link, seen: form };
    formOpen = true;
  }

  function askDelete(link: Link) {
    toDelete = link;
    deleteSeen = form;
    deleteOpen = true;
  }
</script>

<section class="mt-10" aria-labelledby="links-heading">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <h2 id="links-heading" class="text-lg font-semibold">Links</h2>
    <button
      type="button"
      class="rounded bg-black px-4 py-2 text-white"
      aria-haspopup="dialog"
      aria-controls="link-form"
      onclick={() => openForm(null)}
    >
      + Link
    </button>
  </div>

  {#if links.length}
    <ul class="mt-4 flex flex-col gap-3">
      {#each links as n (n.id)}
        <li class="rounded border p-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-bold wrap-anywhere">{n.label}</span>
            <span class="ml-auto flex items-center gap-4">
              <button
                type="button"
                class="text-sm underline"
                aria-haspopup="dialog"
                aria-controls="link-form"
                onclick={() => openForm(n)}
              >
                Bearbeiten<span class="sr-only">: Link {n.label}</span>
              </button>
              <button
                type="button"
                class="text-sm text-red-800 underline"
                aria-haspopup="dialog"
                aria-controls="link-delete"
                onclick={() => askDelete(n)}
              >
                Löschen<span class="sr-only">: Link {n.label}</span>
              </button>
            </span>
          </div>
          <!-- External address, not an app route, so resolve() does not apply. -->
          <!-- eslint-disable svelte/no-navigation-without-resolve -->
          <a
            href={n.url}
            target="_blank"
            rel="noopener noreferrer"
            class="mt-2 inline-block text-sm break-all underline">{n.url}</a
          >
          <!-- eslint-enable svelte/no-navigation-without-resolve -->
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mt-2 text-sm text-gray-600">Noch keine Links.</p>
  {/if}
</section>

<FormDialog
  id="link-form"
  heading={session.link ? 'Link bearbeiten' : 'Link anlegen'}
  action={session.link ? '?/updateLink' : '?/createLink'}
  submitLabel={session.link ? 'Speichern' : 'Anlegen'}
  bind:open={formOpen}
  message={failed?.message ?? null}
>
  {#key session}
    {#if session.link}<input type="hidden" name="id" value={session.link.id} />{/if}

    <label for="link-label" class="text-sm font-medium">Bezeichnung</label>
    <input
      id="link-label"
      name="label"
      type="text"
      value={values.label}
      class="rounded border px-3 py-2"
      aria-invalid={errors.label ? 'true' : undefined}
      aria-describedby={errors.label ? 'link-label-error' : undefined}
    />
    {#if errors.label}<p id="link-label-error" class="text-sm text-red-800">{errors.label}</p>{/if}

    <label for="link-url" class="text-sm font-medium">Adresse</label>
    <input
      id="link-url"
      name="url"
      type="url"
      value={values.url}
      class="rounded border px-3 py-2"
      aria-invalid={errors.url ? 'true' : undefined}
      aria-describedby={errors.url ? 'link-url-error' : undefined}
    />
    {#if errors.url}<p id="link-url-error" class="text-sm text-red-800">{errors.url}</p>{/if}
  {/key}
</FormDialog>

<FormDialog
  id="link-delete"
  heading="Link löschen?"
  action="?/deleteLink"
  submitLabel="Löschen"
  danger
  bind:open={deleteOpen}
  message={deleteFailed?.message ?? null}
>
  <input type="hidden" name="id" value={toDelete?.id} />
  <p class="text-sm">„{toDelete?.label}“ wird endgültig gelöscht.</p>
</FormDialog>
