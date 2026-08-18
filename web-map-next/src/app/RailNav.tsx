import { useAuthStore, useUiStore, type SidebarTab } from '../lib/store';
import { Tooltip } from '../components/ui';

const TABS: { id: SidebarTab; title: string; path: string; adminOnly?: boolean }[] = [
  { id: 'assets', title: 'Assets', path: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z' },
  { id: 'optimize', title: 'Optimization', path: 'M13 2 4 14h6l-1 8 9-12h-6l1-8z' },
  { id: 'layers', title: 'Layers', path: 'M12 2l9 5-9 5-9-5 9-5zM3 12l9 5 9-5M3 17l9 5 9-5' },
  { id: 'bom', title: 'BOM', path: 'M9 2h6l1 4H8l1-4zM6 6h12l1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L6 6z' },
  { id: 'audit', title: 'Audit', path: 'M9 11H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h4m0-10V7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-9m0-10v12' },
  {
    id: 'admin',
    title: 'Users',
    adminOnly: true,
    path: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75'
  }
];

/** Button box (38px) plus the 2px gap between them — the pitch the indicator travels on. */
const TAB_PITCH = 40;

export function RailNav() {
  const activeSidebarTab = useUiStore((s) => s.activeSidebarTab);
  const setActiveSidebarTab = useUiStore((s) => s.setActiveSidebarTab);
  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const role = useAuthStore((s) => s.role);

  // Hiding the tab is presentation only — the endpoints enforce the same rule server-side.
  const visibleTabs = TABS.filter((tab) => !tab.adminOnly || role === 'ROLE_ADMIN');
  const activeIndex = visibleTabs.findIndex((t) => t.id === activeSidebarTab);

  return (
    <nav aria-label="Workspace sections" className="w-[50px] flex-none bg-panel border-r border-border flex flex-col items-center pt-2.5 gap-0.5">
      <div className="relative flex flex-col items-center gap-0.5">
        {/* One indicator that travels, rather than one per tab appearing and disappearing. The
            movement is what shows the two tabs are related positions in the same list. */}
        {activeIndex >= 0 && (
          <span
            aria-hidden="true"
            className="absolute left-[-10px] w-0.5 h-[22px] rounded bg-accent transition-transform duration-base ease-spring"
            style={{ top: 8, transform: `translateY(${activeIndex * TAB_PITCH}px)` }}
          />
        )}

        {visibleTabs.map((tab) => {
          const active = activeSidebarTab === tab.id;
          return (
            <Tooltip key={tab.id} label={tab.title}>
              <button
                // The e2e suite selects these by aria-label. It previously used the native `title`,
                // which had to go — a native tooltip and the Radix one both fire on hover.
                aria-label={tab.title}
                aria-current={active ? 'page' : undefined}
                onClick={() => {
                  // Clicking the tab you are already on collapses the panel and gives the space to
                  // the map, which is the gesture people reach for once they know the rail.
                  if (active) toggleSidebar();
                  else {
                    setActiveSidebarTab(tab.id);
                    if (sidebarCollapsed) toggleSidebar();
                  }
                }}
                className={`relative w-[38px] h-[38px] flex items-center justify-center rounded-lg border border-transparent
                            transition-[color,background-color] duration-fast ease-out active:scale-95 ${
                              active
                                ? 'text-accent bg-accentSoft'
                                : 'text-textFaint hover:text-textMuted hover:bg-surface2'
                            }`}
              >
                <svg viewBox="0 0 24 24" className="w-[17px] h-[17px]" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d={tab.path} />
                </svg>
              </button>
            </Tooltip>
          );
        })}
      </div>
    </nav>
  );
}
