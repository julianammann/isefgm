<script lang="ts">
  let { open = $bindable(), url }: { open: boolean; url: string } = $props();

  let dialog: HTMLDialogElement | undefined = $state();
  let input: HTMLInputElement | undefined = $state();
  let copied = $state(false);

  $effect(() => {
    if (open && dialog && !dialog.open) {
      copied = false;
      dialog.showModal();
    }
    if (!open && dialog?.open) dialog.close();
  });

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      copied = true;
    } catch {
      // No clipboard access (e.g. plain http): select the text so Cmd/Ctrl+C copies it.
      input?.select();
    }
  }
</script>

<dialog
  id="share-created"
  bind:this={dialog}
  aria-labelledby="share-created-heading"
  class="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-2xl rounded border bg-white p-6 wrap-anywhere shadow-xl backdrop:bg-black/40"
  onclose={() => (open = false)}
>
  <h2 id="share-created-heading" class="text-lg font-semibold">Link erstellt</h2>
  <label for="share-created-url" class="mt-4 block text-sm font-medium">Teilen-Link</label>
  <div class="mt-1 flex gap-2">
    <input
      id="share-created-url"
      bind:this={input}
      readonly
      value={url}
      onfocus={(e) => e.currentTarget.select()}
      class="min-w-0 flex-1 rounded border px-3 py-2"
    />
    <!-- The button itself confirms the copy; the status below tells screen readers. -->
    <button
      type="button"
      class="rounded px-4 py-2 whitespace-nowrap text-white {copied ? 'bg-green-800' : 'bg-black'}"
      onclick={copy}
    >
      {copied ? 'Link kopiert!' : 'Kopieren'}
    </button>
  </div>
  <p role="status" class="sr-only">{copied ? 'Link kopiert' : ''}</p>
  <p class="mt-2 text-sm">
    <strong>Nur jetzt sichtbar:</strong> Der Link lässt sich später nicht noch einmal anzeigen. Geht er
    verloren, lege einen neuen an.
  </p>
  <div class="mt-4">
    <button type="button" class="rounded border px-4 py-2" onclick={() => dialog?.close()}>
      Fertig
    </button>
  </div>
</dialog>
