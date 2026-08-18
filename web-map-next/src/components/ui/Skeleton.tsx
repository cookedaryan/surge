import clsx from 'clsx';

interface SkeletonProps {
  className?: string;
  /** Renders n stacked bars with a shortened last line, the usual shape of a loading paragraph. */
  lines?: number;
}

/**
 * Placeholder for content that is on its way.
 *
 * <p>Marked `aria-hidden` and paired with a visually hidden live message by the caller where the
 * wait is meaningful. A screen reader announcing a row of decorative grey bars tells the operator
 * nothing; "Loading assets" does.
 */
export function Skeleton({ className, lines }: SkeletonProps) {
  if (lines && lines > 1) {
    return (
      <div className="flex flex-col gap-1.5" aria-hidden="true">
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className={clsx('skeleton h-3', i === lines - 1 && 'w-2/3', className)} />
        ))}
      </div>
    );
  }
  return <div aria-hidden="true" className={clsx('skeleton h-3', className)} />;
}
