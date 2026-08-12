import { useUiStore, type SidebarTab } from '../lib/store';

const TABS: { id: SidebarTab; title: string; path: string }[] = [
  { id: 'assets', title: 'Assets', path: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z' },
  { id: 'optimize', title: 'Optimization', path: 'M13 2 4 14h6l-1 8 9-12h-6l1-8z' },
  { id: 'layers', title: 'Layers', path: 'M12 2l9 5-9 5-9-5 9-5zM3 12l9 5 9-5M3 17l9 5 9-5' },
  { id: 'bom', title: 'BOM', path: 'M9 2h6l1 4H8l1-4zM6 6h12l1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L6 6z' },
  { id: 'audit', title: 'Audit', path: 'M9 11H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h4m0-10V7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-9m0-10v12' }
];

export function RailNav() {
  const activeSidebarTab = useUiStore((s) => s.activeSidebarTab);
  const setActiveSidebarTab = useUiStore((s) => s.setActiveSidebarTab);

  return (
    <nav className="w-[50px] flex-none bg-panel border-r border-border flex flex-col items-center pt-2.5 gap-0.5">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          title={tab.title}
          onClick={() => setActiveSidebarTab(tab.id)}
          className={`relative w-[38px] h-[38px] flex items-center justify-center rounded-lg border border-transparent ${
            activeSidebarTab === tab.id ? 'text-accent bg-accentSoft' : 'text-textFaint hover:text-textMuted hover:bg-surface2'
          }`}
        >
          {activeSidebarTab === tab.id && (
            <span className="absolute -left-2.5 top-2 bottom-2 w-0.5 rounded bg-accent" />
          )}
          <svg viewBox="0 0 24 24" className="w-[17px] h-[17px]" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d={tab.path} />
          </svg>
        </button>
      ))}
    </nav>
  );
}
