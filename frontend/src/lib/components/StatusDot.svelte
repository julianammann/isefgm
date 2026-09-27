<script lang="ts">
  import type { SystemStatus } from '$lib/health';

  let { status }: { status: SystemStatus } = $props();

  const color = { ok: 'bg-green-500', degraded: 'bg-amber-500', down: 'bg-red-600' };
</script>

<!-- A button so the tooltip also opens by keyboard; the text is its accessible name,
     so the state never depends on colour alone (Q-07). -->
<span class="group relative flex">
  <button
    type="button"
    aria-label={status.label}
    class="size-2.5 cursor-default rounded-full {color[status.level]}"
  ></button>
  <span
    aria-hidden="true"
    class="invisible absolute top-full right-0 z-10 mt-2 rounded bg-gray-900 px-2 py-1 text-xs whitespace-nowrap text-white group-focus-within:visible group-hover:visible"
  >
    {status.label}
  </span>
</span>
