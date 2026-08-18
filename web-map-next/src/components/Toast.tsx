import { useEffect } from 'react';
import { useUiStore, type ToastItem, type ToastVariant } from '../lib/store';

/** Errors stay up long enough to actually read; success and info can fade quickly. */
const DURATION_MS: Record<ToastVariant, number> = {
  error: 8000,
  success: 3000,
  info: 3000
};

const VARIANT_CLASSES: Record<ToastVariant, string> = {
  success: 'bg-success text-[#04160F] border-success',
  error: 'bg-danger text-white border-danger',
  info: 'bg-surface3 text-text border-borderStrong'
};

const ICONS: Record<ToastVariant, string> = {
  success: 'M20 6 9 17l-5-5',
  error: 'M12 8v5m0 3.5h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  info: 'M12 16v-4m0-4h.01M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z'
};

function ToastRow({ toast }: { toast: ToastItem }) {
  const dismissToast = useUiStore((s) => s.dismissToast);

  useEffect(() => {
    const timer = setTimeout(() => dismissToast(toast.id), DURATION_MS[toast.variant]);
    return () => clearTimeout(timer);
  }, [toast.id, toast.variant, dismissToast]);

  return (
    <div
      // An error is assertive so it interrupts; the rest are polite and wait for a pause. Marking
      // every toast assertive would make a routine "export complete" talk over whatever the
      // operator was actually reading.
      role={toast.variant === 'error' ? 'alert' : 'status'}
      className={`pointer-events-auto animate-slide-up flex items-start gap-2.5 rounded-lg border shadow-3
                  px-3.5 py-2.5 text-sm font-semibold max-w-[520px] ${VARIANT_CLASSES[toast.variant]}`}
    >
      <svg viewBox="0 0 24 24" className="w-4 h-4 flex-none mt-px" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d={ICONS[toast.variant]} />
      </svg>
      <span className="flex-1 leading-snug">{toast.message}</span>
      <button
        onClick={() => dismissToast(toast.id)}
        aria-label="Dismiss notification"
        className="flex-none -mr-1 -mt-0.5 w-5 h-5 inline-flex items-center justify-center rounded opacity-70 hover:opacity-100 transition-opacity duration-fast"
      >
        <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export function Toast() {
  const toasts = useUiStore((s) => s.toasts);

  return (
    // Always mounted so the live region exists before a message arrives. A region inserted at the
    // same moment as its first message is frequently not announced at all.
    <div
      aria-live="polite"
      aria-atomic="false"
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[20050] flex flex-col items-center gap-2 pointer-events-none"
    >
      {toasts.map((t) => (
        <ToastRow key={t.id} toast={t} />
      ))}
    </div>
  );
}
