<script lang="ts">
  import { onMount } from 'svelte';
  import FormDialog from '$lib/components/FormDialog.svelte';
  import {
    GIFTING_STATUS,
    GIFTING_STATUS_CLASS,
    GIFTING_STATUS_ORDER,
    TASK_STATUS,
    TASK_STATUS_ORDER,
    formatDate,
    type GiftingStatus
  } from '$lib/display';
  import type { ActionData, PageData } from './$types';

  type Gifting = PageData['giftings'][number];
  type Task = PageData['tasksByGifting'][string][number];

  let {
    gift,
    giftings,
    tasksByGifting,
    people,
    occasions,
    form
  }: Pick<PageData, 'gift' | 'giftings' | 'tasksByGifting' | 'people' | 'occasions'> & {
    form: ActionData;
  } = $props();

  let formOpen = $state(false);
  let deleteOpen = $state(false);
  let toDelete = $state.raw<Gifting | null>(null);
  /** The action result present when the delete dialog opened, so an older failure stays hidden. */
  let deleteSeen = $state.raw<ActionData>(null);
  /**
   * One opening of the form dialog: the gifting to edit (null for a new one) and the action
   * result present at that moment, which belongs to an earlier opening. A new object per
   * opening re-creates the fields with fresh values.
   */
  let session = $state.raw<{ gifting: Gifting | null; seen: ActionData }>({
    gifting: null,
    seen: null
  });

  const failed = $derived(form !== session.seen && form?.scope === 'gifting' ? form : null);
  const values = $derived(
    failed?.values ?? {
      status: session.gifting?.status ?? 'idea',
      // A new gifting starts with the idea's possible recipients.
      person_ids: (session.gifting ?? gift).people.map((p) => p.id),
      occasion_id: session.gifting?.occasion?.id ?? null,
      occasion_date: session.gifting?.occasion_date ?? null,
      given_on: session.gifting?.given_on ?? null
    }
  );
  const errors = $derived(failed?.errors ?? {});
  // The status select drives which fields are required; it starts from the loaded values.
  let status = $derived<GiftingStatus>(values.status ?? 'idea');

  let taskFormOpen = $state(false);
  let taskDeleteOpen = $state(false);
  let taskToDelete = $state.raw<Task | null>(null);
  let taskDeleteSeen = $state.raw<ActionData>(null);
  // A failed delete keeps its dialog open; only the open delete dialog shows the message.
  const deleteFailed = $derived(
    deleteOpen && form !== deleteSeen && form?.scope === 'delete' ? form : null
  );
  const taskDeleteFailed = $derived(
    taskDeleteOpen && form !== taskDeleteSeen && form?.scope === 'delete' ? form : null
  );
  /**
   * One opening of the task dialog, same pattern as `session`: the gifting the task belongs to
   * (null on a bare idea, which then gets a gifting with the task) and the task to edit.
   */
  let taskSession = $state.raw<{ giftingId: string | null; task: Task | null; seen: ActionData }>({
    giftingId: null,
    task: null,
    seen: null
  });
  const taskFailed = $derived(form !== taskSession.seen && form?.scope === 'task' ? form : null);
  const taskValues = $derived(
    taskFailed?.values ?? {
      title: taskSession.task?.title ?? '',
      status: taskSession.task?.status ?? 'open',
      due_on: taskSession.task?.due_on ?? null
    }
  );
  const taskErrors = $derived(taskFailed?.errors ?? {});
  const taskAction = $derived(
    taskSession.task
      ? '?/updateTask'
      : taskSession.giftingId
        ? '?/createTask'
        : '?/createTaskForGift'
  );

  function openTaskForm(giftingId: string | null, task: Task | null) {
    taskSession = { giftingId, task, seen: form };
    taskFormOpen = true;
  }

  function askDeleteTask(task: Task) {
    taskToDelete = task;
    taskDeleteSeen = form;
    taskDeleteOpen = true;
  }

  let today = $state('');
  onMount(() => {
    today = new Date().toLocaleDateString('sv-SE');
  });

  function openForm(gifting: Gifting | null) {
    session = { gifting, seen: form };
    formOpen = true;
  }

  function askDelete(gifting: Gifting) {
    toDelete = gifting;
    deleteSeen = form;
    deleteOpen = true;
  }
</script>

<section class="mt-10" aria-labelledby="giftings-heading">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <h2 id="giftings-heading" class="text-lg font-semibold">Beschenkungen</h2>
    <span class="flex flex-wrap items-center gap-3">
      {#if giftings.length === 0}
        <button
          type="button"
          class="rounded border px-4 py-2"
          aria-haspopup="dialog"
          aria-controls="task-form"
          aria-describedby="task-bare-hint"
          onclick={() => openTaskForm(null, null)}
        >
          + Aufgabe
        </button>
      {/if}
      <button
        type="button"
        class="rounded bg-black px-4 py-2 text-white"
        aria-haspopup="dialog"
        aria-controls="gifting-form"
        onclick={() => openForm(null)}
      >
        + Beschenkung
      </button>
    </span>
  </div>
  {#if giftings.length === 0}
    <p id="task-bare-hint" class="mt-2 text-sm text-gray-600">
      „+ Aufgabe“ legt eine Beschenkung mit Status ‚Idee‘ an.
    </p>
  {/if}

  {#if giftings.length}
    <ul class="mt-4 flex flex-col gap-3">
      {#each giftings as g (g.id)}
        {@const who = g.people.map((p) => p.name).join(', ')}
        {@const tasks = tasksByGifting[g.id] ?? []}
        <li class="rounded border p-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm">
              <span class="font-bold">{who || 'Noch keine Empfänger:innen'}</span>
              {#if g.occasion}<span class="ml-2 text-gray-600"
                  >{g.occasion.name} {formatDate(g.occasion_date)}</span
                >{/if}
              {#if g.given_on}<span class="ml-2 text-gray-600">
                  verschenkt am {formatDate(g.given_on)}</span
                >{/if}
            </span>
            <span class="ml-auto flex items-center gap-4">
              <button
                type="button"
                class="text-sm underline"
                aria-haspopup="dialog"
                aria-controls="gifting-form"
                onclick={() => openForm(g)}
              >
                Bearbeiten<span class="sr-only">: Beschenkung{who ? ` für ${who}` : ''}</span>
              </button>
              <button
                type="button"
                class="text-sm text-red-800 underline"
                aria-haspopup="dialog"
                aria-controls="gifting-delete"
                onclick={() => askDelete(g)}
              >
                Löschen<span class="sr-only">: Beschenkung{who ? ` für ${who}` : ''}</span>
              </button>
            </span>
          </div>

          <div class="mt-3 flex items-center gap-2">
            <span
              class={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm ${GIFTING_STATUS_CLASS[g.status]}`}
              data-status={g.status}
            >
              <span aria-hidden="true">{GIFTING_STATUS[g.status].icon}</span>
              {GIFTING_STATUS[g.status].label}
            </span>
          </div>

          <div class="mt-4 border-t pt-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <h3 class="text-sm font-semibold">Aufgaben</h3>
              <button
                type="button"
                class="text-sm underline"
                aria-haspopup="dialog"
                aria-controls="task-form"
                onclick={() => openTaskForm(g.id, null)}
              >
                + Aufgabe<span class="sr-only"> zur Beschenkung{who ? ` für ${who}` : ''}</span>
              </button>
            </div>
            {#if tasks.length}
              <ul class="mt-2 flex flex-col gap-2">
                {#each tasks as t (t.id)}
                  <li class="flex flex-wrap items-center gap-2 text-sm">
                    <span data-status={t.status}>
                      <span aria-hidden="true">{TASK_STATUS[t.status].icon}</span>
                      {TASK_STATUS[t.status].label} – {t.title}
                    </span>
                    {#if t.due_on}<span class="text-gray-600">fällig {formatDate(t.due_on)}</span
                      >{/if}
                    <span class="ml-auto flex items-center gap-4">
                      <button
                        type="button"
                        class="underline"
                        aria-haspopup="dialog"
                        aria-controls="task-form"
                        onclick={() => openTaskForm(g.id, t)}
                      >
                        Bearbeiten<span class="sr-only">: Aufgabe {t.title}</span>
                      </button>
                      <button
                        type="button"
                        class="text-red-800 underline"
                        aria-haspopup="dialog"
                        aria-controls="task-delete"
                        onclick={() => askDeleteTask(t)}
                      >
                        Löschen<span class="sr-only">: Aufgabe {t.title}</span>
                      </button>
                    </span>
                  </li>
                {/each}
              </ul>
            {:else}
              <p class="mt-2 text-sm text-gray-600">Noch keine Aufgaben.</p>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mt-2 text-sm text-gray-600">Noch keine Beschenkung.</p>
  {/if}
</section>

<FormDialog
  id="gifting-form"
  heading={session.gifting ? 'Beschenkung bearbeiten' : 'Beschenkung anlegen'}
  action={session.gifting ? '?/updateGifting' : '?/createGifting'}
  submitLabel={session.gifting ? 'Speichern' : 'Anlegen'}
  bind:open={formOpen}
  message={failed?.message ?? null}
>
  {#key session}
    {#if session.gifting}<input type="hidden" name="id" value={session.gifting.id} />{/if}

    <label for="gifting-status" class="text-sm font-medium">Status</label>
    <select
      id="gifting-status"
      name="status"
      bind:value={status}
      class="rounded border px-3 py-2"
      aria-invalid={errors.status ? 'true' : undefined}
      aria-describedby={errors.status ? 'gifting-status-error' : undefined}
    >
      {#each GIFTING_STATUS_ORDER as s (s)}
        <option value={s}>{GIFTING_STATUS[s].label}</option>
      {/each}
    </select>
    {#if errors.status}
      <p id="gifting-status-error" class="text-sm text-red-800">{errors.status}</p>
    {/if}

    <fieldset
      class="flex flex-col gap-2"
      aria-describedby={errors.person_ids ? 'gifting-person-ids-error' : undefined}
    >
      <legend class="text-sm font-medium">
        Tatsächliche Empfänger:innen{status === 'given' ? '' : ' (optional)'}
      </legend>
      {#if people.length === 0}
        <p class="text-sm text-gray-600">Noch keine Personen angelegt.</p>
      {:else}
        <div class="max-h-36 overflow-y-auto rounded border p-3">
          {#each people as person (person.id)}
            <label class="flex items-center gap-2 py-1 text-sm">
              <input
                type="checkbox"
                name="person_ids"
                value={person.id}
                checked={(values.person_ids ?? []).includes(person.id)}
              />
              {person.name}
            </label>
          {/each}
        </div>
      {/if}
      {#if errors.person_ids}
        <p id="gifting-person-ids-error" class="text-sm text-red-800">{errors.person_ids}</p>
      {/if}
    </fieldset>

    <label for="gifting-occasion_id" class="text-sm font-medium">
      Anlass{status === 'given' ? '' : ' (optional)'}
    </label>
    <select
      id="gifting-occasion_id"
      name="occasion_id"
      required={status === 'given'}
      value={values.occasion_id ?? ''}
      class="rounded border px-3 py-2"
      aria-invalid={errors.occasion_id ? 'true' : undefined}
      aria-describedby={errors.occasion_id ? 'gifting-occasion-id-error' : undefined}
    >
      <option value="">– bitte wählen –</option>
      {#each occasions as occasion (occasion.id)}
        <option value={occasion.id}>{occasion.name}</option>
      {/each}
    </select>
    {#if errors.occasion_id}
      <p id="gifting-occasion-id-error" class="text-sm text-red-800">{errors.occasion_id}</p>
    {/if}

    <label for="gifting-occasion_date" class="text-sm font-medium">
      Anlasstermin{status === 'given' ? '' : ' (optional)'}
    </label>
    <input
      id="gifting-occasion_date"
      name="occasion_date"
      type="date"
      required={status === 'given'}
      value={values.occasion_date ?? ''}
      class="rounded border px-3 py-2"
      aria-invalid={errors.occasion_date ? 'true' : undefined}
      aria-describedby={errors.occasion_date ? 'gifting-occasion-date-error' : undefined}
    />
    {#if errors.occasion_date}
      <p id="gifting-occasion-date-error" class="text-sm text-red-800">{errors.occasion_date}</p>
    {/if}

    <!-- Hidden instead of removed, so a quick status change keeps the entered date. -->
    <div class="flex flex-col gap-3" hidden={status !== 'given'}>
      <label for="gifting-given_on" class="text-sm font-medium">Verschenkdatum</label>
      <input
        id="gifting-given_on"
        name="given_on"
        type="date"
        required
        disabled={status !== 'given'}
        value={values.given_on ?? today}
        class="rounded border px-3 py-2"
        aria-invalid={errors.given_on ? 'true' : undefined}
        aria-describedby={errors.given_on ? 'gifting-given-on-error' : undefined}
      />
      {#if errors.given_on}
        <p id="gifting-given-on-error" class="text-sm text-red-800">{errors.given_on}</p>
      {/if}
    </div>
  {/key}
</FormDialog>

<FormDialog
  id="gifting-delete"
  heading="Beschenkung löschen?"
  action="?/deleteGifting"
  submitLabel="Löschen"
  danger
  bind:open={deleteOpen}
  message={deleteFailed?.message ?? null}
>
  <input type="hidden" name="id" value={toDelete?.id} />
  <p class="text-sm">
    Die Beschenkung wird mit ihren Aufgaben endgültig gelöscht. Die Geschenkidee, die Personen und
    der Anlass bleiben erhalten.
  </p>
</FormDialog>

<FormDialog
  id="task-form"
  heading={taskSession.task ? 'Aufgabe bearbeiten' : 'Aufgabe anlegen'}
  action={taskAction}
  submitLabel={taskSession.task ? 'Speichern' : 'Anlegen'}
  bind:open={taskFormOpen}
  message={taskFailed?.message ?? null}
>
  {#key taskSession}
    {#if taskSession.task}<input type="hidden" name="id" value={taskSession.task.id} />{/if}
    {#if taskSession.giftingId}
      <input type="hidden" name="gifting_id" value={taskSession.giftingId} />
    {:else}
      <p class="text-sm text-gray-600">Legt eine Beschenkung mit Status ‚Idee‘ an.</p>
    {/if}

    <label for="task-title" class="text-sm font-medium">Titel</label>
    <input
      id="task-title"
      name="title"
      type="text"
      required
      value={taskValues.title ?? ''}
      class="rounded border px-3 py-2"
      aria-invalid={taskErrors.title ? 'true' : undefined}
      aria-describedby={taskErrors.title ? 'task-title-error' : undefined}
    />
    {#if taskErrors.title}
      <p id="task-title-error" class="text-sm text-red-800">{taskErrors.title}</p>
    {/if}

    <label for="task-status" class="text-sm font-medium">Status</label>
    <select
      id="task-status"
      name="status"
      value={taskValues.status ?? 'open'}
      class="rounded border px-3 py-2"
      aria-invalid={taskErrors.status ? 'true' : undefined}
      aria-describedby={taskErrors.status ? 'task-status-error' : undefined}
    >
      {#each TASK_STATUS_ORDER as s (s)}
        <option value={s}>{TASK_STATUS[s].icon} {TASK_STATUS[s].label}</option>
      {/each}
    </select>
    {#if taskErrors.status}
      <p id="task-status-error" class="text-sm text-red-800">{taskErrors.status}</p>
    {/if}

    <label for="task-due_on" class="text-sm font-medium">Fälligkeitsdatum (optional)</label>
    <input
      id="task-due_on"
      name="due_on"
      type="date"
      value={taskValues.due_on ?? ''}
      class="rounded border px-3 py-2"
      aria-invalid={taskErrors.due_on ? 'true' : undefined}
      aria-describedby={taskErrors.due_on ? 'task-due-on-error' : undefined}
    />
    {#if taskErrors.due_on}
      <p id="task-due-on-error" class="text-sm text-red-800">{taskErrors.due_on}</p>
    {/if}
  {/key}
</FormDialog>

<FormDialog
  id="task-delete"
  heading="Aufgabe löschen?"
  action="?/deleteTask"
  submitLabel="Löschen"
  danger
  bind:open={taskDeleteOpen}
  message={taskDeleteFailed?.message ?? null}
>
  <input type="hidden" name="id" value={taskToDelete?.id} />
  <p class="text-sm">Die Aufgabe „{taskToDelete?.title}“ wird endgültig gelöscht.</p>
</FormDialog>
