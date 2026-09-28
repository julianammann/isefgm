<script lang="ts">
  import { enhance } from '$app/forms';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();
</script>

<svelte:head><title>Konto – Geschenke-Manager</title></svelte:head>

<main class="mx-auto max-w-4xl p-8">
  <h1 class="text-2xl font-bold">Konto</h1>
  <dl class="mt-4 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
    <dt class="text-gray-600">Anzeigename</dt>
    <dd>{data.user.display_name}</dd>
    <dt class="text-gray-600">E-Mail-Adresse</dt>
    <dd>{data.user.email}</dd>
  </dl>

  <section class="mt-10 rounded border p-4" aria-labelledby="logout-all-heading">
    <h2 id="logout-all-heading" class="font-semibold">Auf allen Geräten abmelden</h2>
    <p class="mt-2 text-sm">
      Beendet alle Sitzungen dieses Kontos, auch in diesem Browser. Sinnvoll, wenn ein Gerät
      verloren gegangen ist oder jemand anderes angemeldet sein könnte.
    </p>
    <form method="POST" action="?/logoutAll" use:enhance class="mt-4 flex flex-col gap-3">
      {#if form?.logoutAllMessage}
        <p role="alert" class="text-sm text-red-800">{form.logoutAllMessage}</p>
      {/if}
      <button type="submit" class="self-start rounded bg-black px-4 py-2 text-white">
        Auf allen Geräten abmelden
      </button>
    </form>
  </section>

  <section class="mt-10 rounded border border-red-300 p-4" aria-labelledby="delete-heading">
    <h2 id="delete-heading" class="font-semibold text-red-800">Konto löschen</h2>
    <p class="mt-2 text-sm">
      Löscht das Konto mit allen Personen, Anlässen, Geschenkideen, Beschenkungen und Aufgaben
      endgültig.
    </p>
    <form method="POST" action="?/delete" use:enhance class="mt-4 flex flex-col gap-3">
      {#if form?.message}
        <p role="alert" class="text-sm text-red-800">{form.message}</p>
      {/if}
      <label class="flex items-center gap-2 text-sm">
        <input name="confirm" type="checkbox" required />
        Ich möchte mein Konto und alle Daten endgültig löschen.
      </label>
      <button type="submit" class="self-start rounded bg-red-700 px-4 py-2 text-white">
        Konto endgültig löschen
      </button>
    </form>
  </section>
</main>
