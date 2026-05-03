/**
 * Foundational types shared by ChartMetadata, ChartPlugin, and the registries.
 *
 * Mirrors apache/superset's `superset-ui-core/src/chart/types/Base.ts`.
 */

export enum Behavior {
  /** Chart can be the target of dashboard/native filters. */
  NativeFilter = 'NATIVE_FILTER',
  /** Chart receives interactive cross-filter events from siblings. */
  InteractiveChart = 'INTERACTIVE_CHART',
  /** "Drill to detail" right-click menu is supported. */
  DrillToDetail = 'DRILL_TO_DETAIL',
  /** "Drill by" right-click menu is supported. */
  DrillBy = 'DRILL_BY',
}

export enum ChartLabel {
  Featured = 'FEATURED',
  Deprecated = 'DEPRECATED',
  Verified = 'VERIFIED',
}

/**
 * Top-level chart categories used by the viz-picker gallery.
 * Strings (not enum keys) so they show up unmodified in the UI.
 */
export const ChartCategory = {
  Correlation: 'Correlation',
  Distribution: 'Distribution',
  Evolution: 'Evolution',
  Flow: 'Flow',
  KPI: 'KPI',
  Map: 'Map',
  Part: 'Part of a Whole',
  Ranking: 'Ranking',
  Table: 'Table',
  Trend: 'Trend',
  Other: 'Other',
} as const;

export type ChartCategoryName = (typeof ChartCategory)[keyof typeof ChartCategory];

export type ParseMethod = 'json' | 'json-bigint' | 'text';

export interface ExampleImage {
  url: string;
  urlDark?: string;
  caption?: string;
}
