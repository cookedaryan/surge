import { ReactNode } from 'react';

export function MapArea({ children }: { children: ReactNode }) {
  return <main className="flex-1 relative bg-surface2 overflow-hidden">{children}</main>;
}
