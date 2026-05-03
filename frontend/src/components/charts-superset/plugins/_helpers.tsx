/**
 * Plugin authoring helpers — keep boilerplate small for the dozens of
 * not-yet-implemented chart types, while still giving each a real
 * {@link ChartMetadata} entry so they show up in the picker.
 */
import { ComponentType } from 'react';
import { ChartMetadata, ChartMetadataConfig } from '../models/ChartMetadata';
import { ChartPlugin, ChartPluginConfig } from '../models/ChartPlugin';
import type { QueryFormData } from '../models/ChartProps';
import { PlaceholderChart } from '../components/PlaceholderChart';

const UnimplementedChart: ComponentType<{
  width: number;
  height: number;
  className?: string;
  formData?: { viz_type?: string };
  __chartName?: string;
}> = ({ width, height, formData, __chartName, className }) => (
  <PlaceholderChart
    width={width}
    height={height}
    title="Coming soon"
    description="This chart type is registered but a renderer hasn't been wired up yet."
    chartType={formData?.viz_type}
    chartName={__chartName}
    variant="unimplemented"
    className={className}
  />
);

/**
 * Build a fully-formed `ChartPlugin` whose renderer is the placeholder.
 * Used for the long tail of chart types we want present in the catalog
 * before their full implementations land.
 */
export function buildStubPlugin(
  metadataConfig: ChartMetadataConfig,
): ChartPlugin {
  const metadata = new ChartMetadata(metadataConfig);
  return new ChartPlugin({
    metadata,
    loadChart: () => {
      // Wrap so the placeholder gets the chart's display name.
      const Wrapper: ComponentType<any> = (props) => (
        <UnimplementedChart {...props} __chartName={metadata.name} />
      );
      Wrapper.displayName = `StubChart(${metadata.name})`;
      return Wrapper;
    },
  });
}

/**
 * Convenience for declaring a plugin where the heavy bits (renderer,
 * controlPanel, transformProps) live alongside in this file rather than a
 * separate folder. Useful for compact plugins.
 */
export function buildPlugin<F extends QueryFormData = QueryFormData>(
  config: ChartPluginConfig<F>,
): ChartPlugin<F> {
  return new ChartPlugin<F>(config);
}
