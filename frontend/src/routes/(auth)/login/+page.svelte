<script lang="ts">
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();
</script>

<svelte:head><title>Anmelden – Geschenke-Manager</title></svelte:head>

<main class="mx-auto max-w-sm p-8">
  <h1 class="text-2xl font-bold">Anmelden</h1>

  <form
    method="POST"
    use:enhance
    class="mt-6 flex flex-col gap-4"
    aria-describedby={form?.message ? 'form-error' : undefined}
  >
    {#if form?.message}
      <p
        id="form-error"
        role="alert"
        class="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800"
      >
        {form.message}
      </p>
    {/if}

    <label class="flex flex-col gap-1">
      <span>E-Mail-Adresse</span>
      <input
        name="email"
        type="email"
        required
        autocomplete="email"
        value={form?.email ?? ''}
        class="rounded border p-2"
      />
    </label>

    <label class="flex flex-col gap-1">
      <span>Passwort</span>
      <input
        name="password"
        type="password"
        required
        autocomplete="current-password"
        class="rounded border p-2"
      />
    </label>

    <button type="submit" class="rounded bg-black px-4 py-2 text-white">Anmelden</button>
  </form>

  {#if data.registrationEnabled}
    <p class="mt-6 text-sm">
      Noch kein Konto? <a class="underline" href={resolve('/register')}>Registrieren</a>
    </p>
  {/if}
</main>
