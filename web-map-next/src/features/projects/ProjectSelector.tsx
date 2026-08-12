import { useEffect } from 'react';
import { useCreateProject, useProjects } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { Select, Button } from '../../components/ui';
import { NewProjectModal } from './NewProjectModal';

export function ProjectSelector() {
  const { data: projects = [], isSuccess } = useProjects();
  const createProject = useCreateProject();
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const setCurrentProjectId = useUiStore((s) => s.setCurrentProjectId);
  const setNewProjectModalOpen = useUiStore((s) => s.setNewProjectModalOpen);

  useEffect(() => {
    if (!isSuccess) return;
    if (projects.length === 0 && !createProject.isPending && !createProject.data) {
      createProject.mutate({ name: 'Default Workstation Project', description: 'Default Grid Evacuation Workspace' });
      return;
    }
    if (!currentProjectId && projects.length > 0) {
      setCurrentProjectId(projects[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSuccess, projects, currentProjectId]);

  useEffect(() => {
    if (createProject.data && !currentProjectId) setCurrentProjectId(createProject.data.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createProject.data]);

  return (
    <>
      <Select
        value={currentProjectId || ''}
        onValueChange={setCurrentProjectId}
        options={projects.map((p) => ({ value: p.id, label: p.name }))}
        className="min-w-[160px]"
      />
      <Button size="sm" onClick={() => setNewProjectModalOpen(true)}>+ New</Button>
      <NewProjectModal />
    </>
  );
}
