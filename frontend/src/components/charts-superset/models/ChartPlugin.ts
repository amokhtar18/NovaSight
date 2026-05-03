import { ComponentType } from 'react';
import { Plugin } from './Plugin';
import { ChartMetadata } from './ChartMetadata';
import type { ControlPanelConfig } from './ControlPanel';
import type { TransformProps } from './TransformProps';
import type { BuildQuery } from './BuildQuery';
import type { QueryFormData } from './ChartProps';
import getChartMetadataRegistry from '../registries/ChartMetadataRegistrySingleton';
import getChartComponentRegistry from '../registries/ChartComponentRegistrySingleton';
import getChartControlPanelRegistry from '../registries/ChartControlPanelRegistrySingleton';
import getChartTransformPropsRegistry from '../registries/ChartTransformPropsRegistrySingleton';
import getChartBuildQueryRegistry from '../registries/ChartBuildQueryRegistrySingleton';

export type PromiseOrValue<T> = T | Promise<T>;
export type Loader<T> = () => PromiseOrValue<T> | { default: T };

const IDENTITY: TransformProps = (chartProps) =>
  chartProps as unknown as Record<string, unknown>;

export interface ChartPluginConfig<F extends QueryFormData = QueryFormData> {
  metadata: ChartMetadata;
  /** Lazy loader for the renderer component. Use `() => import('./MyChart')`. */
  loadChart: Loader<ComponentType<any>>;
  /** Optional control-panel descriptor. */
  controlPanel?: ControlPanelConfig;
  /** Optional `transformProps` (or a lazy loader of one). Defaults to identity. */
  transformProps?: TransformProps<F>;
  loadTransformProps?: Loader<TransformProps<F>>;
  /** Optional `buildQuery` lazy loader. */
  buildQuery?: BuildQuery<F>;
  loadBuildQuery?: Loader<BuildQuery<F>>;
}

/**
 * A chart plugin packages everything the registries need: metadata,
 * renderer, control panel, transform-props, optional build-query.
 *
 * Faithful to apache/superset's `ChartPlugin`. To register:
 *
 * ```ts
 * new MyChartPlugin().configure({ key: VizType.MyChart }).register();
 * ```
 */
export class ChartPlugin<F extends QueryFormData = QueryFormData> extends Plugin {
  readonly metadata: ChartMetadata;
  readonly controlPanel: ControlPanelConfig | undefined;
  readonly loadChart: Loader<ComponentType<any>>;
  readonly loadTransformProps: Loader<TransformProps<F>>;
  readonly loadBuildQuery?: Loader<BuildQuery<F>>;

  constructor(config: ChartPluginConfig<F>) {
    super();
    const {
      metadata,
      loadChart,
      controlPanel,
      transformProps,
      loadTransformProps,
      buildQuery,
      loadBuildQuery,
    } = config;

    this.metadata = metadata;
    this.controlPanel = controlPanel;
    this.loadChart = loadChart;

    if (loadTransformProps) {
      this.loadTransformProps = loadTransformProps;
    } else if (transformProps) {
      this.loadTransformProps = () => transformProps;
    } else {
      this.loadTransformProps = () => IDENTITY as TransformProps<F>;
    }

    if (loadBuildQuery) {
      this.loadBuildQuery = loadBuildQuery;
    } else if (buildQuery) {
      this.loadBuildQuery = () => buildQuery;
    }
  }

  register(): this {
    const key = this.config.key;
    if (!key) {
      throw new Error(
        `[ChartPlugin] register() called without a key. Did you forget .configure({ key })?`,
      );
    }

    getChartMetadataRegistry().registerValue(key, this.metadata);
    getChartComponentRegistry().registerLoader(key, this.loadChart as any);

    if (this.controlPanel) {
      getChartControlPanelRegistry().registerValue(key, this.controlPanel);
    }

    getChartTransformPropsRegistry().registerLoader(
      key,
      this.loadTransformProps as any,
    );

    if (this.loadBuildQuery) {
      getChartBuildQueryRegistry().registerLoader(
        key,
        this.loadBuildQuery as any,
      );
    }

    return this;
  }
}

export default ChartPlugin;
