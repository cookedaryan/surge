import { FormEvent, useId, useState } from 'react';
import { useUiStore } from '../../lib/store';
import { useCreateProject } from '../../lib/query';
import { Dialog, Button } from '../../components/ui';

export function NewProjectModal() {
  const open = useUiStore((s) => s.newProjectModalOpen);
  const setOpen = useUiStore((s) => s.setNewProjectModalOpen);
  const setCurrentProjectId = useUiStore((s) => s.setCurrentProjectId);
  const createProject = useCreateProject();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const nameId = useId();
  const descId = useId();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || createProject.isPending) return;
    setError(null);
    try {
      const project = await createProject.mutateAsync({ name: name.trim(), description: description.trim() });
      setCurrentProjectId(project.id);
      setName('');
      setDescription('');
      setOpen(false);
    } catch (err) {
      // This used to be an unawaited rejection: the dialog stayed open with the button stuck on
      // "Creating…" and nothing said why. Now the only way to create a project, so a failure that
      // reports nothing would leave the operator with no way into the app at all.
      setError((err as Error).message || 'The project could not be created.');
    }
  }

  function handleOpenChange(next: boolean) {
    if (!next) setError(null);
    setOpen(next);
  }

  const fieldClass =
    'w-full rounded-md border border-borderStrong bg-surface2 px-2.5 text-sm text-text outline-none ' +
    'transition-[border-color,box-shadow] duration-fast ease-out ' +
    'placeholder:text-textFaint focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-100)]';

  return (
    <Dialog
      open={open}
      onOpenChange={handleOpenChange}
      title="New Project"
      description="A project holds one site's assets and every run made against them."
      footer={
        <>
          <Button type="button" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="new-project-form"
            variant="primary"
            loading={createProject.isPending}
            disabled={!name.trim()}
          >
            Create Project
          </Button>
        </>
      }
    >
      {/* A form element so Enter submits — the dialog previously only responded to the button. */}
      <form id="new-project-form" onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div>
          <label htmlFor={nameId} className="mb-1.5 block text-sm text-textMuted">
            Project name
          </label>
          <input
            id={nameId}
            className={`${fieldClass} h-8`}
            placeholder="e.g. Kutch Phase II"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </div>
        <div>
          <label htmlFor={descId} className="mb-1.5 block text-sm text-textMuted">
            Description <span className="text-textFaint">(optional)</span>
          </label>
          <textarea
            id={descId}
            className={`${fieldClass} h-20 resize-none py-2`}
            placeholder="What this site is, and anything worth knowing about it."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        {error && (
          <p role="alert" className="m-0 text-sm text-danger">
            {error}
          </p>
        )}
      </form>
    </Dialog>
  );
}
