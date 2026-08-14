import { useEffect } from 'react';
import { useUiStore } from '../lib/store';

const VARIANT_CLASSES: Record<string, string> = {
  success: 'bg-success',
  error: 'bg-danger',
  info: 'bg-surface2 border border-borderStrong'
};

export function Toast() {
  const toast = useUiStore((s) => s.toast);
  const clearToast = useUiStore((s) => s.clearToast);

  useEffect(() => {
    if (!toast) return;
    // Errors stay up long enough to actually read; success/info can fade quickly.
    const timer = setTimeout(clearToast, toast.variant === 'error' ? 8000 : 3000);
    return () => clearTimeout(timer);
  }, [toast, clearToast]);

  if (!toast) return null;

  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-[20050] text-white text-[13px] font-semibold px-5 py-2.5 rounded-lg shadow-lg max-w-[520px] text-center ${VARIANT_CLASSES[toast.variant]}`}
    >
      {toast.message}
    </div>
  );
}
