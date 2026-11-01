<script lang="ts">
  import type { components } from '$lib/api/schema';
  import FormDialog from '$lib/components/FormDialog.svelte';

  type PersonInput = components['schemas']['PersonIn'];

  let {
    open = $bindable(),
    action,
    editId,
    values,
    errors,
    message,
    keepPosition,
    onclose
  }: {
    open: boolean;
    action: string;
    editId: string | null;
    values: PersonInput;
    errors: Partial<Record<keyof PersonInput, string>>;
    message: string | null;
    /** See `FormDialog`; the list turns it off and keeps SvelteKit's reset after a save. */
    keepPosition?: boolean;
    /** Called when the dialog is dismissed (Escape, Abbrechen), not after a successful save. */
    onclose?: () => void;
  } = $props();

  const isEdit = $derived(editId !== null);
</script>

<FormDialog
  id="person-form-dialog"
  heading={isEdit ? 'Person bearbeiten' : 'Person anlegen'}
  {action}
  submitLabel={isEdit ? 'Speichern' : 'Anlegen'}
  bind:open
  {message}
  {keepPosition}
  {onclose}
>
  {#if editId}<input type="hidden" name="id" value={editId} />{/if}

  <label for="person-name" class="text-sm font-medium">Name</label>
  <input
    id="person-name"
    name="name"
    required
    maxlength="100"
    value={values.name}
    class="rounded border px-3 py-2"
    aria-invalid={errors.name ? 'true' : undefined}
    aria-describedby={errors.name ? 'person-name-error' : undefined}
  />
  {#if errors.name}<p id="person-name-error" class="text-sm text-red-800">{errors.name}</p>{/if}

  <label for="person-birthday" class="text-sm font-medium">Geburtstag (optional)</label>
  <input
    id="person-birthday"
    name="birthday"
    type="date"
    value={values.birthday ?? ''}
    class="rounded border px-3 py-2"
    aria-invalid={errors.birthday ? 'true' : undefined}
    aria-describedby={errors.birthday ? 'person-birthday-error' : undefined}
  />
  {#if errors.birthday}
    <p id="person-birthday-error" class="text-sm text-red-800">{errors.birthday}</p>
  {/if}

  <label for="person-relationship" class="text-sm font-medium">Beziehung (optional)</label>
  <input
    id="person-relationship"
    name="relationship"
    maxlength="100"
    value={values.relationship ?? ''}
    class="rounded border px-3 py-2"
    aria-invalid={errors.relationship ? 'true' : undefined}
    aria-describedby={errors.relationship ? 'person-relationship-error' : undefined}
  />
  {#if errors.relationship}
    <p id="person-relationship-error" class="text-sm text-red-800">{errors.relationship}</p>
  {/if}

  <label for="person-notes" class="text-sm font-medium">Notizen (optional)</label>
  <textarea
    id="person-notes"
    name="notes"
    maxlength="2000"
    class="rounded border px-3 py-2"
    aria-invalid={errors.notes ? 'true' : undefined}
    aria-describedby={errors.notes ? 'person-notes-error' : undefined}
    >{values.notes ?? ''}</textarea
  >
  {#if errors.notes}<p id="person-notes-error" class="text-sm text-red-800">{errors.notes}</p>{/if}
</FormDialog>
