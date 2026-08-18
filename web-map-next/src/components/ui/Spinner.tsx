import clsx from 'clsx';

/**
 * Inline activity indicator.
 *
 * <p>The rotation is a CSS animation rather than an SVG `animateTransform`, so the global
 * `prefers-reduced-motion` override in globals.css stops it along with everything else. Stopped, it
 * still reads as a ring rather than vanishing, which is the point — the element is what says "this
 * control is busy", and under reduced motion that meaning has to survive without the spin.
 */
export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={clsx('animate-spin', className)}
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      style={{ animationDuration: '600ms' }}
    >
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeOpacity={0.25} strokeWidth={2} />
      <path d="M14.5 8A6.5 6.5 0 0 0 8 1.5" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}
