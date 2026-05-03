import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import { ChartCategory, Behavior } from '../../types/Base';
import LineChartPlugin from '../Line';

/**
 * Generic time-series chart — same renderer as {@link LineChartPlugin} but
 * registered under VizType.Timeseries (`echarts_timeseries`) so existing
 * Superset form_data referencing that key continues to render.
 *
 * In a future iteration this will be split out with its own annotation
 * support and event-data overlays.
 */
const lineMetadata = new ChartMetadata({
  name: 'Time-series Chart',
  description:
    'Generic time-series visualization — line/area hybrid with annotations.',
  category: ChartCategory.Evolution,
  tags: ['Featured', 'Time-series', 'Trend', 'Annotations'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
  canBeAnnotationTypes: ['EVENT', 'INTERVAL', 'TIME_SERIES', 'FORMULA'],
});

export default class TimeseriesChartPlugin extends ChartPlugin {
  constructor() {
    const inner = new LineChartPlugin();
    super({
      metadata: lineMetadata,
      loadChart: inner.loadChart,
      loadTransformProps: inner.loadTransformProps,
    });
  }
}
