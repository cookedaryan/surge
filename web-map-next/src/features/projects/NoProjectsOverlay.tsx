import { useProjects } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { Button } from '../../components/ui';

/**
 * What a brand-new account sees instead of a blank map.
 *
 * <p>Once the app stopped inventing a project to put people in, the honest first-run state became
 * an empty workstation — a grey map, panels that all say "select a project", and no indication of
 * what to do. This says it, and offers the one action that helps.
 *
 * <p>Shown only for a list that genuinely came back empty. While the request is in flight or after
 * it has failed the map is left alone: telling someone they have no projects because the server
 * did not answer is the same lie the auto-created project used to tell.
 */
export function NoProjectsOverlay() {
  const { data: projects, isSuccess } = useProjects();
  const setNewProjectModalOpen = useUiStore((s) => s.setNewProjectModalOpen);

  if (!isSuccess || !projects || projects.length > 0) return null;

  return (
    <div className="absolute inset-0 z-[1015] flex items-center justify-center bg-bg/70 backdrop-blur-[2px]">
      <div className="w-[380px] max-w-[88%] animate-slide-up rounded-xl border border-borderStrong bg-panel/95 p-6 text-center shadow-3">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-accentSoft text-accent">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />
          </svg>
        </div>
        <h2 className="m-0 mb-1.5 text-lg font-bold text-text">No projects yet</h2>
        <p className="m-0 mb-4 text-sm leading-relaxed text-textMuted">
          A project holds one site: its turbines, substation and constraints, and every optimisation
          run made against them. Create one, then import a survey to begin.
        </p>
        <Button variant="primary" className="mx-auto h-9 px-4" onClick={() => setNewProjectModalOpen(true)}>
          Create a project
        </Button>
      </div>
    </div>
  );
}
