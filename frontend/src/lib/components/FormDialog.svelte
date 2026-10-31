<script lang="ts">
  import { enhance } from '$app/forms';
  import type { Snippet } from 'svelte';

  let {
    id,
    heading,
    action,
    submitLabel,
    open = $bindable(),
    message = null,
    danger = false,
    enctype,
    children
  }: {
    id: string;
    heading: string;
    action: string;
    submitLabel: string;
    open: boolean;
    message?: string | null;
    danger?: boolean;
    enctype?: 'multipart/form-data';
    children: Snippet;
  } = $props();

  let dialog: HTMLDialogElement | undefined = $state();

  $effect(() => {
    if (open && dialog && !dialog.open) dialog.showModal();
    if (!open && dialog?.open) dialog.close();
  });
</script>

<dialog
  {id}
  bind:this={dialog}
  aria-labelledby="{id}-heading"
  class="fixed inset-0 m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded border bg-white p-6 shadow-xl backdrop:bg-black/40"
  onclose={() => (open = false)}
>
  <h2 id="{id}-heading" class="text-lg font-semibold">{heading}</h2>
  <form
    method="POST"
    {action}
    {enctype}
    use:enhance={() =>
      async ({ result, update }) => {
        if (result.type === 'redirect') dialog?.close();
        await update();
      }}
    novalidate
    class="mt-4 flex flex-col gap-3"
  >
    {#if message}<p role="alert" class="text-sm text-red-800">{message}</p>{/if}
    {@render children()}
    <div class="flex items-center gap-4">
      <button
        type="submit"
        class="rounded px-4 py-2 text-white {danger ? 'bg-red-700' : 'bg-black'}"
      >
        {submitLabel}
      </button>
      <button type="button" class="rounded border px-4 py-2" onclick={() => dialog?.close()}>
        Abbrechen
      </button>
    </div>
  </form>
</dialog>
