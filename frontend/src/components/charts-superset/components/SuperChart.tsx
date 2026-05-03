import { useEffect, useMemo, useState } from 'react';
import {
  getChartComponentRegistry,
  getChartTransformPropsRegistry,
  getChartMetadataRegistry,
} from '../registries';
import type { ChartProps, QueryFormData, ChartDataResponseResult } from '../models/ChartProps';
import { PlaceholderChart } from './PlaceholderChart';

export interface SuperChartProps {
  /** Plugin key (e.g. VizType.Bar). */
  chartType: string;
  width: number;
  height: number;
  /** Form-data persisted on the chart. */
  formData?: Partial<QueryFormData>;
  /** Query results — typically one entry per QueryObject. */
  queriesData?: ChartDataResponseResult[];
  /** Optional className forwarded to the rendered chart. */
  className?: string;
  /** Render in dark mode (color schemes, axis colors, etc.). */
  isDark?: boolean;
  /** Datasource metadata for column/metric introspection. */
  datasource?: ChartProps['datasource'];
  /** Hooks forwarded to the chart component. */
  hooks?: ChartProps['hooks'];
}

/**
 * Universal chart renderer.
 *
 * Looks up the chart's registered React component and `transformProps`
 * function from the registries, awaits any lazy loaders, then renders.
 * Falls back to {@link PlaceholderChart} when the plugin isn't registered
 * or its renderer isn't yet implemented.
 */
export function SuperChart({
  chartType,
  width,
  height,
  formData,
  queriesData = [],
  className,
  datasource,
  hooks,
  isDark,
}: SuperChartProps) {
  const [Component, setComponent] = useState<React.ComponentType<any> | null>(null);
  const [transformProps, setTransformProps] = useState<((p: ChartProps) => any) | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const metadata = useMemo(
    () => getChartMetadataRegistry().get(chartType),
    [chartType],
  );

  useEffect(() => {
    let cancelled = false;
    setError(null);

    Promise.all([
      getChartComponentRegistry().get(chartType),
      getChartTransformPropsRegistry().get(chartType),
    ])
      .then(([component, tp]) => {
        if (cancelled) return;
        setComponent(() => (component ?? null) as React.ComponentType<any> | null);
        setTransformProps(() => (tp ?? null) as ((p: ChartProps) => any) | null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err : new Error(String(err)));
      });

    return () => {
      cancelled = true;
    };
  }, [chartType]);

  if (error) {
    return (
      <PlaceholderChart
        width={width}
        height={height}
        title="Chart failed to load"
        description={error.message}
        chartType={chartType}
        chartName={metadata?.name}
        variant="error"
      />
    );
  }

  if (!metadata) {
    return (
      <PlaceholderChart
        width={width}
        height={height}
        title="Unknown chart type"
        description={`No plugin registered for "${chartType}". Did you call MainPreset.register()?`}
        chartType={chartType}
        variant="error"
      />
    );
  }

  if (!Component || !transformProps) {
    return (
      <PlaceholderChart
        width={width}
        height={height}
        title="Loading chart"
        chartType={chartType}
        chartName={metadata.name}
        variant="loading"
      />
    );
  }

  const chartProps: ChartProps = {
    width,
    height,
    formData: { viz_type: chartType, ...(formData ?? {}) } as QueryFormData,
    queriesData,
    datasource,
    hooks,
  };

  let mappedProps: Record<string, unknown>;
  try {
    mappedProps = transformProps(chartProps) ?? {};
  } catch (err) {
    return (
      <PlaceholderChart
        width={width}
        height={height}
        title="Chart configuration error"
        description={err instanceof Error ? err.message : String(err)}
        chartType={chartType}
        chartName={metadata.name}
        variant="error"
      />
    );
  }

  return (
    <Component
      width={width}
      height={height}
      className={className}
      isDark={isDark}
      {...mappedProps}
    />
  );
}

export default SuperChart;
