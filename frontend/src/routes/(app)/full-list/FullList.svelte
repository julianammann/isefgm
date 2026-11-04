<!-- Injected: the downloaded document has no app stylesheet, so render() puts the styles in its head. -->
<svelte:options css="injected" />

<script lang="ts">
  import type { components } from '#lib/api/schema.js';
  import { CATEGORIES, formatDate, formatPriceRange } from '#lib/display.js';

  let { list }: { list: components['schemas']['FullListOut'] } = $props();

  const names = (people: { name: string }[]) => people.map((p) => p.name).join(', ');
</script>

<svelte:head><title>Vollständige Liste – Geschenke-Manager</title></svelte:head>

<main>
  <h1>Vollständige Liste</h1>

  <section aria-labelledby="people-heading">
    <h2 id="people-heading">Personen</h2>
    {#if list.people.length}
      <table>
        <thead>
          <tr><th>Name</th><th>Geburtstag</th><th>Beziehung</th><th>Notizen</th></tr>
        </thead>
        <tbody>
          {#each list.people as person (person.id)}
            <tr>
              <td>{person.name}</td>
              <td>{formatDate(person.birthday)}</td>
              <td>{person.relationship ?? ''}</td>
              <td>{person.notes ?? ''}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p>Keine Personen.</p>
    {/if}
  </section>

  <section aria-labelledby="gifts-heading">
    <h2 id="gifts-heading">Geschenkideen</h2>
    {#each list.gifts as gift (gift.id)}
      <article>
        <h3>{gift.title}</h3>
        {#if gift.description}<p>{gift.description}</p>{/if}
        <dl>
          <dt>Kategorie</dt>
          <dd>{CATEGORIES[gift.category]}</dd>
          {#if formatPriceRange(gift)}
            <dt>Preis</dt>
            <dd>{formatPriceRange(gift)}</dd>
          {/if}
          {#if gift.people.length}
            <dt>Für</dt>
            <dd>{names(gift.people)}</dd>
          {/if}
          {#if gift.occasions.length}
            <dt>Anlässe</dt>
            <dd>{names(gift.occasions)}</dd>
          {/if}
          {#if gift.links.length}
            <dt>Links</dt>
            <dd>
              <ul>
                <!-- External addresses (backend accepts only http and https), not app routes. -->
                <!-- eslint-disable svelte/no-navigation-without-resolve -->
                {#each gift.links as link (link.id)}
                  <li><a href={link.url}>{link.label}</a></li>
                {/each}
                <!-- eslint-enable svelte/no-navigation-without-resolve -->
              </ul>
            </dd>
          {/if}
          {#each gift.notes as note (note.id)}
            <dt>{note.label}</dt>
            <dd>{note.text}</dd>
          {/each}
        </dl>
      </article>
    {:else}
      <p>Keine Geschenkideen.</p>
    {/each}
  </section>

  <section aria-labelledby="given-heading">
    <h2 id="given-heading">Vergangene Geschenke</h2>
    {#if list.given.length}
      <table>
        <thead>
          <tr
            ><th>Geschenk</th><th>Für</th><th>Anlass</th><th>Anlasstermin</th><th>Verschenkt am</th
            ></tr
          >
        </thead>
        <tbody>
          {#each list.given as gifting (gifting.id)}
            <tr>
              <td>{gifting.gift.title}</td>
              <td>{names(gifting.people)}</td>
              <td>{gifting.occasion?.name ?? ''}</td>
              <td>{formatDate(gifting.occasion_date)}</td>
              <td>{formatDate(gifting.given_on)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p>Keine vergangenen Geschenke.</p>
    {/if}
  </section>
</main>

<style>
  main {
    max-width: 60rem;
    margin: 0 auto;
    padding: 1rem;
    font-family: system-ui, sans-serif;
    line-height: 1.5;
  }
  section {
    margin-top: 2rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    border: 1px solid #ccc;
    padding: 0.25rem 0.5rem;
    text-align: left;
    vertical-align: top;
  }
  article {
    border-top: 1px solid #ccc;
    padding-top: 0.5rem;
  }
  dl {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 0.25rem 1rem;
  }
  dt {
    color: #555;
  }
  dd {
    margin: 0;
  }
  ul {
    margin: 0;
    padding-left: 1.25rem;
  }
</style>
