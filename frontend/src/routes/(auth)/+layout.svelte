<script lang="ts">
  import StatusDot from '$lib/components/StatusDot.svelte';
  import type { LayoutProps } from './$types';

  let { data, children }: LayoutProps = $props();
</script>

<!-- Login and registration: the status dot shows an outage before anyone types a password. -->
<header class="border-b">
  <div class="mx-auto flex max-w-4xl items-center p-4">
    <span class="font-bold">Geschenke-Manager</span>
    <span class="ml-auto"><StatusDot status={data.status} /></span>
  </div>
</header>

{@render children()}
