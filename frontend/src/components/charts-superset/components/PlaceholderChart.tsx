import { AlertCircle, Loader2, Construction } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PlaceholderChartProps {
  width: number | string;
  height: number | string;
  title: string;
  description?: string;
  chartType?: string;
  chartName?: string;
  variant?: 'unimplemented' | 'loading' | 'error';
  className?: string;
}

/**
 * Visual fallback shown while a chart is loading, when no implementation is
 * available yet, or when configuration is invalid.
 */
export function PlaceholderChart({
  width,
  height,
  title,
  description,
  chartType,
  chartName,
  variant = 'unimplemented',
  className,
}: PlaceholderChartProps) {
  const Icon =
    variant === 'loading'
      ? Loader2
      : variant === 'error'
      ? AlertCircle
      : Construction;

  const tone =
    variant === 'error'
      ? 'border-destructive/40 bg-destructive/5 text-destructive'
      : variant === 'loading'
      ? 'border-border bg-muted/30 text-muted-foreground'
      : 'border-amber-500/30 bg-amber-500/5 text-amber-700 dark:text-amber-300';

  return (
    <div
      role="img"
      aria-label={`${title}${chartName ? `: ${chartName}` : ''}`}
      style={{ width, height }}
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-4 text-center',
        tone,
        className,
      )}
    >
      <Icon
        className={cn('h-8 w-8', variant === 'loading' && 'animate-spin')}
        aria-hidden
      />
      <div className="text-sm font-medium">{title}</div>
      {chartName && (
        <div className="text-xs opacity-80">
          {chartName}
          {chartType ? <span className="opacity-60"> · {chartType}</span> : null}
        </div>
      )}
      {description && (
        <div className="max-w-md text-xs opacity-75">{description}</div>
      )}
    </div>
  );
}

export default PlaceholderChart;
