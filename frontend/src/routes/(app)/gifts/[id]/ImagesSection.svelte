<script lang="ts">
  import FormDialog from '$lib/components/FormDialog.svelte';
  import { IMAGE_TYPES, MAX_IMAGES, imageFileError } from '$lib/images';
  import type { ActionData, PageData } from './$types';

  type Image = PageData['images'][number];

  let { images, form }: Pick<PageData, 'images'> & { form: ActionData } = $props();

  let formOpen = $state(false);
  let deleteOpen = $state(false);
  let toDelete = $state.raw<Image | null>(null);
  /** The action result present when the delete dialog opened, so an older failure stays hidden. */
  let deleteSeen = $state.raw<ActionData>(null);
  /**
   * One opening of the form dialog: the image to relabel (null for an upload) and the action
   * result present at that moment, which belongs to an earlier opening.
   */
  let session = $state.raw<{ image: Image | null; seen: ActionData }>({
    image: null,
    seen: null
  });
  let fileError = $state<string | undefined>();
  /** Whether the file input holds a file; it keeps it after a failed submit. */
  let hasFile = $state(false);

  // A failed delete keeps its dialog open; only the open delete dialog shows the message.
  const deleteFailed = $derived(
    deleteOpen && form !== deleteSeen && form?.scope === 'delete' ? form : null
  );
  const failed = $derived(form !== session.seen && form?.scope === 'image' ? form : null);
  const label = $derived(failed?.values?.label ?? session.image?.label ?? '');
  const errors = $derived(failed?.errors ?? {});
  const labelMessage = $derived('label' in errors ? errors.label : undefined);
  // The server's file error shows until the user picks another file.
  let serverFileError = $derived('file' in errors ? errors.file : undefined);
  const fileMessage = $derived(fileError ?? serverFileError);
  const full = $derived(images.length >= MAX_IMAGES);

  function openForm(image: Image | null) {
    session = { image, seen: form };
    fileError = undefined;
    hasFile = false;
    formOpen = true;
  }

  function askDelete(image: Image) {
    toDelete = image;
    deleteSeen = form;
    deleteOpen = true;
  }

  /** Blocks the submit of the surrounding form while the chosen file is invalid. */
  function guardSubmit(input: HTMLInputElement) {
    const block = (event: Event) => {
      if (fileError) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };
    // Kept from mount: `input.form` is already null once the input is removed.
    const formElement = input.form;
    formElement?.addEventListener('submit', block, true);
    return { destroy: () => formElement?.removeEventListener('submit', block, true) };
  }
</script>

<section class="mt-10" aria-labelledby="images-heading">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <h2 id="images-heading" class="text-lg font-semibold">Bilder ({images.length}/{MAX_IMAGES})</h2>
    <div class="flex items-center gap-3">
      {#if full}<span id="image-limit" class="text-sm text-gray-600"
          >Höchstens {MAX_IMAGES} Bilder pro Idee.</span
        >{/if}
      <button
        type="button"
        class="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        aria-haspopup="dialog"
        aria-controls="image-form"
        aria-describedby={full ? 'image-limit' : undefined}
        disabled={full}
        onclick={() => openForm(null)}
      >
        + Bild
      </button>
    </div>
  </div>

  {#if images.length}
    <ul class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
      {#each images as image (image.id)}
        <li class="rounded border p-3">
          <img
            src="/api/v1/images/{image.id}/content"
            alt={image.label}
            loading="lazy"
            class="h-48 w-full rounded object-contain"
          />
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <span class="text-sm font-bold wrap-anywhere">{image.label}</span>
            <span class="ml-auto flex items-center gap-4">
              <button
                type="button"
                class="text-sm underline"
                aria-haspopup="dialog"
                aria-controls="image-form"
                onclick={() => openForm(image)}
              >
                Bearbeiten<span class="sr-only">: Bild {image.label}</span>
              </button>
              <button
                type="button"
                class="text-sm text-red-800 underline"
                aria-haspopup="dialog"
                aria-controls="image-delete"
                onclick={() => askDelete(image)}
              >
                Löschen<span class="sr-only">: Bild {image.label}</span>
              </button>
            </span>
          </div>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mt-2 text-sm text-gray-600">Noch keine Bilder.</p>
  {/if}
</section>

<FormDialog
  id="image-form"
  heading={session.image ? 'Bild bearbeiten' : 'Bild hochladen'}
  action={session.image ? '?/updateImage' : '?/createImage'}
  submitLabel={session.image ? 'Speichern' : 'Hochladen'}
  enctype={session.image ? undefined : 'multipart/form-data'}
  bind:open={formOpen}
  message={failed?.message ?? null}
>
  {#key session}
    {#if session.image}<input type="hidden" name="id" value={session.image.id} />{/if}

    <label for="image-label" class="text-sm font-medium">Bezeichnung</label>
    <input
      id="image-label"
      name="label"
      type="text"
      value={label}
      class="rounded border px-3 py-2"
      aria-invalid={labelMessage ? 'true' : undefined}
      aria-describedby={labelMessage ? 'image-label-error' : undefined}
    />
    {#if labelMessage}
      <p id="image-label-error" class="text-sm text-red-800">{labelMessage}</p>
    {/if}

    {#if !session.image}
      <label for="image-file" class="text-sm font-medium">Bild</label>
      <input
        id="image-file"
        name="file"
        type="file"
        accept={IMAGE_TYPES.join(',')}
        use:guardSubmit
        onchange={(e) => {
          const file = e.currentTarget.files?.[0] ?? null;
          fileError = imageFileError(file);
          hasFile = file !== null;
          serverFileError = undefined;
        }}
        aria-invalid={fileMessage ? 'true' : undefined}
        aria-describedby={fileMessage ? 'image-file-error' : undefined}
      />
      {#if failed && !hasFile}
        <p class="text-sm text-gray-600">Bitte wähle das Bild erneut aus.</p>
      {/if}
      {#if fileMessage}
        <p id="image-file-error" class="text-sm text-red-800">{fileMessage}</p>
      {/if}
    {/if}
  {/key}
</FormDialog>

<FormDialog
  id="image-delete"
  heading="Bild löschen?"
  action="?/deleteImage"
  submitLabel="Löschen"
  danger
  bind:open={deleteOpen}
  message={deleteFailed?.message ?? null}
>
  <input type="hidden" name="id" value={toDelete?.id} />
  <p class="text-sm">„{toDelete?.label}“ wird endgültig gelöscht.</p>
</FormDialog>
