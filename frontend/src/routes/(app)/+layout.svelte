<script lang="ts">
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import StatusDot from '$lib/components/StatusDot.svelte';
  import type { LayoutProps } from './$types';

  let { data, children }: LayoutProps = $props();
</script>

<header class="border-b">
  <nav class="mx-auto flex max-w-4xl items-center gap-6 p-4" aria-label="Hauptnavigation">
    <a class="font-bold" href={resolve('/')}>Geschenke-Manager</a>
    <span class="ml-auto flex items-center gap-2 text-sm">
      <StatusDot status={data.status} />
      {data.user.display_name}
    </span>
    <a class="text-sm underline" href={resolve('/account')}>Konto</a>
    <form method="POST" action="/logout" use:enhance>
      <button type="submit" class="text-sm underline">Abmelden</button>
    </form>
  </nav>
</header>

{@render children()}
