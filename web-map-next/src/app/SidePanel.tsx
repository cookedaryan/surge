import { ReactNode } from 'react';
import { useUiStore, type SidebarTab } from '../lib/store';

interface PaneProps {
  tab: SidebarTab;
  children: ReactNode;
}

export function Pane({ tab, children }: PaneProps) {
  const activeSidebarTab = useUiStore((s) => s.activeSidebarTab);
  if (activeSidebarTab !== tab) return null;
  return <div className="flex flex-col gap-3">{children}</div>;
}

export function SidePanel({ children }: { children: ReactNode }) {
  return (
    <aside className="w-[300px] flex-none bg-panel border-r border-border overflow-y-auto p-3.5">
      {children}
    </aside>
  );
}
