<script lang="ts">
  import { page } from '$app/state';
  import { CATEGORIES, formatDate, formatPriceRange } from '#lib/display.js';
  import type { PageProps } from './$types';

  let { data }: PageProps = $props();

  const shared = $derived(data.shared);
</script>

<svelte:head>
  <title>Geschenkideen von {shared.owner_name} – Geschenke-Manager</title>
</svelte:head>

<main class="mx-auto max-w-4xl p-8">
  <p class="text-sm font-bold">Geschenke-Manager</p>
  <h1 class="mt-4 text-2xl font-bold">Geschenkideen von {shared.owner_name}</h1>
  <p class="mt-2 text-sm text-gray-600">
    {shared.owner_name} hat diese Ideen mit dir geteilt. Du kannst sie nur ansehen.
    {#if data.expires_on}Der Link ist gültig bis {formatDate(data.expires_on)}.{/if}
  </p>

  {#each shared.people as person, i (i)}
    <section class="mt-10" aria-labelledby="person-{i}">
      <h2 id="person-{i}" class="text-lg font-semibold">
        Für {person.name} ({person.gifts.length})
      </h2>
      {#if person.gifts.length === 0}
        <p class="mt-2 text-sm text-gray-600">Noch keine Ideen.</p>
      {:else}
        <ul class="mt-3 flex flex-col gap-3">
          {#each person.gifts as gift, g (g)}
            {@const price = formatPriceRange(gift)}
            <li class="rounded border p-3">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="font-semibold">{gift.title}</h3>
                <span class="rounded-full border px-2 py-0.5 text-sm">
                  {CATEGORIES[gift.category]}
                </span>
              </div>
              {#if price}<p class="mt-1 text-sm text-gray-600">{price}</p>{/if}
              {#if gift.description}
                <p class="mt-2 text-sm whitespace-pre-line">{gift.description}</p>
              {/if}
              {#if gift.links.length}
                <ul class="mt-2 flex flex-col gap-1 text-sm" aria-label="Links zu {gift.title}">
                  {#each gift.links as link, l (l)}
                    <li>
                      <!-- Opens the shop in a new tab without telling it where the visit came from. -->
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer external"
                        class="underline">{link.label}</a
                      >
                    </li>
                  {/each}
                </ul>
              {/if}
              {#if gift.images.length}
                <div class="mt-3 flex flex-wrap gap-3">
                  {#each gift.images as image (image.id)}
                    <img
                      src="/api/v1/shared/{page.params.token}/images/{image.id}"
                      alt={image.label}
                      loading="lazy"
                      class="h-32 w-32 rounded border object-cover"
                    />
                  {/each}
                </div>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  {/each}
</main>
