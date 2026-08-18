import * as RadixDialog from '@radix-ui/react-dialog';
import { ReactNode } from 'react';

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  widthClassName?: string;
}

/**
 * A panel that enters from the right, over the map rather than instead of it.
 *
 * <p>Built on Radix Dialog for the focus trap, escape handling and scroll lock, but deliberately
 * given a lighter scrim than {@link Dialog}. The results this carries are read *against* the route
 * they describe, and a modal-weight overlay would black out the thing the operator is checking.
 */
export function Sheet({ open, onOpenChange, title, subtitle, children, widthClassName = 'w-[640px]' }: SheetProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/35 z-[9990] data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <RadixDialog.Content
          className={`fixed right-0 top-0 bottom-0 ${widthClassName} max-w-[94vw] z-[10000] flex flex-col
                      bg-panel border-l border-borderStrong shadow-3 font-ui text-text
                      data-[state=open]:animate-slide-in-right data-[state=closed]:animate-slide-out-right`}
        >
          <header className="flex-none flex items-start gap-3 px-4 py-3 border-b border-border">
            <div className="min-w-0 flex-1">
              <RadixDialog.Title className="m-0 text-base font-bold text-text">{title}</RadixDialog.Title>
              {subtitle && <div className="mt-0.5 text-sm text-textFaint">{subtitle}</div>}
            </div>
            <RadixDialog.Close
              aria-label="Close"
              className="flex-none w-7 h-7 inline-flex items-center justify-center rounded-md text-textFaint
                         hover:text-text hover:bg-surface2 transition-colors duration-fast ease-out"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </RadixDialog.Close>
          </header>
          <div className="flex-1 min-h-0 overflow-y-auto p-4">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

/**
 * One section of a sheet, entering slightly after the one above it.
 *
 * <p>The stagger is a delay on a single animation, not a timeline — under reduced motion the
 * duration collapses and every section is simply present, with no residual delay to sit through.
 */
export function SheetSection({
  title,
  index = 0,
  children
}: {
  title?: string;
  index?: number;
  children: ReactNode;
}) {
  return (
    <section
      className="animate-slide-up mb-4 last:mb-0"
      style={{ animationDelay: `${Math.min(index, 8) * 45}ms`, animationFillMode: 'backwards' }}
    >
      {title && (
        <h4 className="m-0 mb-2 text-sm font-bold uppercase tracking-wide text-textMuted">{title}</h4>
      )}
      {children}
    </section>
  );
}
