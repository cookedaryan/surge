import { useState } from 'react';
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

  async function handleSave() {
    if (!name.trim()) return;
    const project = await createProject.mutateAsync({ name: name.trim(), description: description.trim() });
    setCurrentProjectId(project.id);
    setName('');
    setDescription('');
    setOpen(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title="New Project"
      footer={
        <>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="primary" disabled={createProject.isPending || !name.trim()} onClick={handleSave}>
            {createProject.isPending ? 'Creating…' : 'Create Project'}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <input
          className="h-8 rounded-md border border-borderStrong bg-surface2 px-2.5 text-[11.5px] text-text outline-none focus:border-accent"
          placeholder="Project name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <textarea
          className="rounded-md border border-borderStrong bg-surface2 px-2.5 py-2 text-[11.5px] text-text outline-none focus:border-accent resize-none h-20"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
    </Dialog>
  );
}
