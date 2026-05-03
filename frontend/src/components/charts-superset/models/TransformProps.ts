import type { ChartProps, QueryFormData } from './ChartProps';

/**
 * `transformProps` reshapes a {@link ChartProps} object into the props its
 * React component actually consumes.
 */
export type TransformProps<
  F extends QueryFormData = QueryFormData,
  Out = Record<string, unknown>,
> = (chartProps: ChartProps<F>) => Out;
