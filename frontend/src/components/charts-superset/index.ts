/**
 * Public entry point for the Superset-style chart-plugin system.
 *
 * Usage:
 *
 * ```tsx
 * import { setupChartsSuperset, SuperChart, VizType } from '@/components/charts-superset';
 *
 * // once, at app startup
 * setupChartsSuperset();
 *
 * // anywhere
 * <SuperChart
 *   chartType={VizType.Bar}
 *   width={600}
 *   height={400}
 *   formData={{ viz_type: VizType.Bar, metrics: ['sales'], groupby: ['region'] }}
 *   queriesData={[{ data: rows }]}
 * />
 * ```
 */

// ── Types ──────────────────────────────────────────────────────────────
export { VizType } from './types/VizType';
export { Behavior, ChartCategory, ChartLabel } from './types/Base';
export type { ChartCategoryName, ExampleImage, ParseMethod } from './types/Base';

// ── Models ─────────────────────────────────────────────────────────────
export { ChartMetadata } from './models/ChartMetadata';
export type { ChartMetadataConfig } from './models/ChartMetadata';
export { ChartPlugin } from './models/ChartPlugin';
export type { ChartPluginConfig, Loader, PromiseOrValue } from './models/ChartPlugin';
export { Plugin } from './models/Plugin';
export { Preset } from './models/Preset';
export type {
  ChartProps,
  QueryFormData,
  ChartDataResponseResult,
} from './models/ChartProps';
export type { TransformProps } from './models/TransformProps';
export type { BuildQuery, QueryObject, QueryContext } from './models/BuildQuery';
export type {
  ControlConfig,
  ControlPanelConfig,
  ControlPanelSectionConfig,
  ControlSetItem,
  ControlSetRow,
  ControlType,
} from './models/ControlPanel';

// ── Registries ─────────────────────────────────────────────────────────
export {
  getChartMetadataRegistry,
  getChartComponentRegistry,
  getChartControlPanelRegistry,
  getChartTransformPropsRegistry,
  getChartBuildQueryRegistry,
} from './registries';

// ── Components ─────────────────────────────────────────────────────────
export { SuperChart, PlaceholderChart, ChartGallery } from './components';
export type {
  SuperChartProps,
  PlaceholderChartProps,
  ChartGalleryProps,
} from './components';

// ── Styling ────────────────────────────────────────────────────────────
export {
  SUPERSET_COLORS,
  D3_CATEGORY_10,
  D3_CATEGORY_20,
  GOOGLE_CATEGORY_20C,
  BNB_COLORS,
  LYFT_COLORS,
  PRESET_COLORS,
  getCategoricalScheme,
  nthColor,
} from './styling/colorSchemes';
export type { CategoricalScheme } from './styling/colorSchemes';
export { getSequentialScheme } from './styling/sequentialSchemes';
export * from './styling/theme';

// ── Bootstrap ──────────────────────────────────────────────────────────
export { default as MainPreset } from './presets/MainPreset';
export { setupChartsSuperset, isChartsSupersetReady } from './setup';
