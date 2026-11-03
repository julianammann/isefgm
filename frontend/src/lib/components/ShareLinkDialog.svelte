<script lang="ts">
  import FormDialog from '#lib/components/FormDialog.svelte';
  import { berlinDate } from '#lib/expiry.js';

  type Values = { person_ids: string[]; expires_on: string | null };

  let {
    id,
    heading,
    submitLabel,
    action,
    open = $bindable(),
    people,
    values,
    errors,
    message,
    linkId = null,
    active = true,
    currentExpiresAt = null
  }: {
    id: string;
    heading: string;
    submitLabel: string;
    action: string;
    open: boolean;
    /** Everyone who can be picked. */
    people: { id: string; name: string }[];
    values: Values;
    errors: Partial<Record<keyof Values, string>>;
    message: string | null;
    /** The link being edited; null when a new one is created. */
    linkId?: string | null;
    /** Active flag of the edited link; an edit keeps it, only the toggle changes it. */
    active?: boolean;
    /** Stored expiry of the edited link, sent back so an unchanged day keeps it. */
    currentExpiresAt?: string | null;
  } = $props();

  const today = berlinDate(new Date());
</script>

<FormDialog {id} {heading} {action} {submitLabel} bind:open {message}>
  {#if linkId}
    <input type="hidden" name="id" value={linkId} />
    <input type="hidden" name="active" value={String(active)} />
  {/if}
  {#if currentExpiresAt}
    <input type="hidden" name="current_expires_at" value={currentExpiresAt} />
  {/if}

  <!-- A group has no invalid state; the error is tied to it as its description. -->
  <fieldset aria-describedby={errors.person_ids ? `${id}-people-error` : undefined}>
    <legend class="text-sm font-medium">Personen, deren Ideen der Link zeigt</legend>
    <div class="mt-2 flex max-h-60 flex-col gap-1 overflow-y-auto rounded border p-3">
      {#each people as person (person.id)}
        <label class="flex items-center gap-2">
          <input
            type="checkbox"
            name="person_ids"
            value={person.id}
            checked={values.person_ids.includes(person.id)}
          />
          {person.name}
        </label>
      {/each}
    </div>
  </fieldset>
  {#if errors.person_ids}
    <p id="{id}-people-error" class="text-sm text-red-800">{errors.person_ids}</p>
  {/if}

  <label for="{id}-expires" class="text-sm font-medium">Gültig bis einschließlich (optional)</label>
  <input
    id="{id}-expires"
    name="expires_on"
    type="date"
    min={today}
    value={values.expires_on ?? ''}
    class="rounded border px-3 py-2"
    aria-invalid={errors.expires_on ? 'true' : undefined}
    aria-describedby="{id}-expires-hint{errors.expires_on ? ` ${id}-expires-error` : ''}"
  />
  <p id="{id}-expires-hint" class="text-sm text-gray-600">Leer lassen für unbegrenzt.</p>
  {#if errors.expires_on}
    <p id="{id}-expires-error" class="text-sm text-red-800">{errors.expires_on}</p>
  {/if}

  <p class="text-sm text-gray-600">
    Wer den Link hat, sieht ohne Anmeldung die Namen und Geschenkideen dieser Personen, mit Links
    und Bildern. Notizen, Beschenkungen und Anlässe bleiben privat.
  </p>
</FormDialog>
