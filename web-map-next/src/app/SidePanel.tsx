import { ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import { useUiStore, SIDEBAR_MIN_WIDTH, SIDEBAR_MAX_WIDTH, type SidebarTab } from '../lib/store';

interface PaneProps {
  tab: SidebarTab;
  children: ReactNode;
}

/**
 * One section of the side panel.
 *
 * <p>Mounted lazily on first visit and kept mounted after that, hidden with CSS rather than
 * unmounted. Unmounting discarded whatever the operator had set up — the scenario, the three
 * sliders — the moment they looked at another tab, which for a run they were midway through
 * configuring is silent data loss.
 *
 * <p>Keeping panes alive is affordable here specifically because the query client sets
 * `refetchOnWindowFocus: false` and no refetch interval, so a hidden pane issues no traffic. The
 * lazy first mount is what stops all six firing their queries on load.
 */
export function Pane({ tab, children }: PaneProps) {
  const activeSidebarTab = useUiStore((s) => s.activeSidebarTab);
  const isActive = activeSidebarTab === tab;
  const [everActive, setEverActive] = useState(isActive);

  useEffect(() => {
    if (isActive) setEverActive(true);
  }, [isActive]);

  if (!everActive) return null;

  return (
    <div
      // `hidden` rather than unmounting keeps state; it also keeps the subtree out of the
      // accessibility tree and the tab order, which display:none does correctly.
      hidden={!isActive}
      className={isActive ? 'flex flex-col gap-3 animate-fade-in' : undefined}
    >
      {children}
    </div>
  );
}

export function SidePanel({ children }: { children: ReactNode }) {
  const width = useUiStore((s) => s.sidebarWidth);
  const setSidebarWidth = useUiStore((s) => s.setSidebarWidth);
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const [dragging, setDragging] = useState(false);
  const asideRef = useRef<HTMLElement>(null);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  useEffect(() => {
    if (!dragging) return;

    const onMove = (e: PointerEvent) => {
      const left = asideRef.current?.getBoundingClientRect().left ?? 0;
      setSidebarWidth(e.clientX - left);
    };
    const onUp = () => setDragging(false);

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    // Held on the body rather than the handle so the cursor stays consistent when the pointer
    // outruns the drag and ends up over the map.
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [dragging, setSidebarWidth]);

  return (
    <aside
      ref={asideRef}
      aria-label="Workspace panel"
      style={{ width: collapsed ? 0 : width }}
      // min-w-0 is load-bearing, not defensive. A flex item's automatic minimum size is its
      // content's, so without it the panel refuses to shrink below the ~300px its cards occupy and
      // collapsing sets width:0 to no visible effect.
      className={`relative flex-none min-w-0 bg-panel border-r border-border ${
        collapsed ? 'overflow-hidden border-r-0' : 'overflow-y-auto'
      } ${
        // Animating width during a drag would make the panel lag the pointer.
        dragging ? '' : 'transition-[width] duration-base ease-out'
      }`}
    >
      <div className="p-3.5" style={{ width: collapsed ? width : undefined }}>
        {children}
      </div>

      {!collapsed && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panel"
          aria-valuenow={width}
          aria-valuemin={SIDEBAR_MIN_WIDTH}
          aria-valuemax={SIDEBAR_MAX_WIDTH}
          tabIndex={0}
          onPointerDown={onPointerDown}
          // Resizable by keyboard too. A drag handle that only answers to a pointer is a control
          // some operators simply do not have.
          onKeyDown={(e) => {
            if (e.key === 'ArrowLeft') setSidebarWidth(width - 16);
            else if (e.key === 'ArrowRight') setSidebarWidth(width + 16);
            else return;
            e.preventDefault();
          }}
          className={`absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize z-10
                      transition-colors duration-fast ease-out hover:bg-accent/40 ${dragging ? 'bg-accent/60' : ''}`}
        />
      )}

      {!collapsed && (
        <button
          onClick={toggleSidebar}
          aria-label="Collapse panel"
          className="sticky bottom-2 left-full ml-[-30px] mb-2 flex h-6 w-6 items-center justify-center rounded-md
                     border border-border bg-surface2 text-textFaint shadow-1
                     transition-colors duration-fast ease-out hover:text-text hover:border-borderStrong"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18 9 12l6-6" />
          </svg>
        </button>
      )}
    </aside>
  );
}
