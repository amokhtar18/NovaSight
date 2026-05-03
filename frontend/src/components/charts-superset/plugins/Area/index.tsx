import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { ChartCategory, Behavior } from '../../types/Base';
import { getCategoricalScheme, nthColor } from '../../styling/colorSchemes';
import {
  CHART_AXIS_COLOR,
  CHART_DEFAULT_MARGIN,
  CHART_FONT_FAMILY,
  CHART_GRID_COLOR,
} from '../../styling/theme';

interface AreaFormData extends QueryFormData {
  groupby?: string[];
  metrics?: string[];
  color_scheme?: string;
  stacked?: boolean;
  smooth?: boolean;
  show_legend?: boolean;
  x_axis?: string;
}

function AreaChartViz(props: {
  width: number;
  height: number;
  data: Record<string, unknown>[];
  xKey: string;
  metrics: string[];
  colorScheme: string;
  stacked: boolean;
  smooth: boolean;
  showLegend: boolean;
  className?: string;
}) {
  const { width, height, data, xKey, metrics, colorScheme, stacked, smooth, showLegend, className } = props;
  const scheme = getCategoricalScheme(colorScheme);
  return (
    <div style={{ width, height }} className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={CHART_DEFAULT_MARGIN}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_COLOR} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12, fontFamily: CHART_FONT_FAMILY, fill: CHART_AXIS_COLOR }} />
          <YAxis tick={{ fontSize: 12, fontFamily: CHART_FONT_FAMILY, fill: CHART_AXIS_COLOR }} />
          <Tooltip />
          {showLegend && <Legend />}
          {metrics.map((m, i) => {
            const color = nthColor(scheme, i);
            return (
              <Area
                key={m}
                type={smooth ? 'monotone' : 'linear'}
                dataKey={m}
                stackId={stacked ? 'stack' : undefined}
                stroke={color}
                fill={color}
                fillOpacity={0.3}
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const transformProps: TransformProps<AreaFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<AreaFormData>;
  const data = queriesData[0]?.data ?? [];
  const sample = data[0] ?? {};
  const xKey =
    formData.x_axis ??
    formData.groupby?.[0] ??
    Object.keys(sample).find((k) => typeof sample[k] !== 'number') ??
    Object.keys(sample)[0] ??
    '';
  const metrics = formData.metrics?.length
    ? formData.metrics
    : Object.keys(sample).filter((k) => typeof sample[k] === 'number');
  return {
    width,
    height,
    data,
    xKey,
    metrics,
    colorScheme: formData.color_scheme ?? 'supersetColors',
    stacked: formData.stacked !== false,
    smooth: formData.smooth !== false,
    showLegend: formData.show_legend !== false,
  };
};

const metadata = new ChartMetadata({
  name: 'Area Chart',
  description:
    'Stacked or overlaid filled areas — emphasises magnitude over a continuous axis.',
  category: ChartCategory.Evolution,
  tags: ['Featured', 'Time-series', 'Continuous', 'Trend', 'Stack'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
  canBeAnnotationTypes: ['EVENT', 'INTERVAL', 'TIME_SERIES', 'FORMULA'],
});

export default class AreaChartPlugin extends ChartPlugin<AreaFormData> {
  constructor() {
    super({ metadata, loadChart: () => AreaChartViz, transformProps });
  }
}
