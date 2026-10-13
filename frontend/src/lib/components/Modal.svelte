<script>
  let { showModal = $bindable(), header, children } = $props();

  let dialog = $state(); // HTMLDialogElement

  $effect(() => {
    if (showModal) dialog.showModal();
  });
</script>

<dialog
  bind:this={dialog}
  onclose={() => (showModal = false)}
  onclick={(e) => {
    if (e.target === dialog) dialog.close();
  }}
  class="open:animate-zoom open:backdrop:animate-fade m-auto max-w-[32em] rounded-[0.2em]
		border-none
		p-0 backdrop:bg-black/30"
>
  <div class="p-4">
    {@render header?.()}
    <hr class="my-2" />
    {@render children?.()}
    <hr class="my-2" />
    <!-- svelte-ignore a11y_autofocus -->
    <button autofocus onclick={() => dialog.close()} class="block">close modal</button>
  </div>
</dialog>
