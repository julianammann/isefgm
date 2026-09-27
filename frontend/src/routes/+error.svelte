<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
</script>

<main class="mx-auto max-w-2xl p-8">
  <h1 class="text-3xl font-bold">{page.status}</h1>
  <p class="mt-4">{page.error?.message ?? 'Unbekannter Fehler'}</p>
  <a class="mt-4 inline-block underline" href={resolve('/')}>Zur Startseite</a>
</main>
