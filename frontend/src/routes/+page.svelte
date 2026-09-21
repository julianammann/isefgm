<script lang="ts">
  import { api } from '$lib/api/client';

  let status = $state('Backend wird geprüft ...');

  $effect(() => {
    void api.GET('/api/v1/health/ready').then(({ data, response }) => {
      status = data
        ? `Backend: ${data.status}, Datenbank: ${data.database ? 'verbunden' : 'getrennt'} `
        : `Backend nicht erreichbar (HTTP ${String(response.status)})`;
    });
  });
</script>

<main class="mx-auto max-w-2xl p-8">
  <h1 class="text-3xl font-bold">Geschenke Manager</h1>
  <p class="mt-4">{status}</p>
</main>
