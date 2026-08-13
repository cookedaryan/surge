import { useEffect } from 'react';
import { useUiStore } from '../lib/store';

export function Toast() {
  const toast = useUiStore((s) => s.toast);
  const clearToast = useUiStore((s) => s.clearToast);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(clearToast, 3000);
    return () => clearTimeout(timer);
  }, [toast, clearToast]);

  if (!toast) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[20050] bg-success text-white text-[13px] font-semibold px-5 py-2.5 rounded-lg shadow-lg">
      {toast}
    </div>
  );
}
