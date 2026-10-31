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
    onclose,
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
    /** Called when the dialog is dismissed (Escape, Abbrechen), not after a successful save. */
    onclose?: () => void;
    children: Snippet;
  } = $props();

  let dialog: HTMLDialogElement | undefined = $state();
  /** True while a request runs; the disabled submit button prevents a second save. */
  let pending = $state(false);
  /** True while a successful save redirects, so closing the dialog does not call `onclose`. */
  let saving = false;

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
  onclose={() => {
    open = false;
    if (!saving) onclose?.();
  }}
>
  <h2 id="{id}-heading" class="text-lg font-semibold">{heading}</h2>
  <form
    method="POST"
    {action}
    {enctype}
    use:enhance={() => {
      pending = true;
      return async ({ result, update }) => {
        if (result.type === 'redirect') {
          saving = true;
          dialog?.close();
        }
        await update();
        saving = false;
        pending = false;
      };
    }}
    novalidate
    aria-busy={pending}
    class="mt-4 flex flex-col gap-3"
  >
    {#if message}<p role="alert" class="text-sm text-red-800">{message}</p>{/if}
    {@render children()}
    <div class="flex items-center gap-4">
      <button
        type="submit"
        disabled={pending}
        class="rounded px-4 py-2 text-white disabled:opacity-50 {danger
          ? 'bg-red-700'
          : 'bg-black'}"
      >
        {submitLabel}
      </button>
      <!-- A delete confirmation starts on Abbrechen, not on the destructive button; inside a
           <dialog>, autofocus is the standard way to choose the first focus. -->
      <!-- svelte-ignore a11y_autofocus -->
      <button
        type="button"
        class="rounded border px-4 py-2"
        autofocus={danger}
        onclick={() => dialog?.close()}
      >
        Abbrechen
      </button>
    </div>
  </form>
</dialog>
