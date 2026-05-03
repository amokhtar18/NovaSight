import {
  BarChart,
  Bar,
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

interface BarFormData extends QueryFormData {
  groupby?: string[];
  metrics?: string[];
  color_scheme?: string;
  stacked?: boolean;
  orientation?: 'vertical' | 'horizontal';
  show_legend?: boolean;
  x_axis_label?: string;
  y_axis_label?: string;
}

interface BarRendererProps {
  width: number;
  height: number;
  data: Record<string, unknown>[];
  xKey: string;
  metrics: string[];
  colorScheme: string;
  stacked: boolean;
  showLegend: boolean;
  xAxisLabel?: string;
  yAxisLabel?: string;
  className?: string;
}

function BarChartViz({
  width,
  height,
  data,
  xKey,
  metrics,
  colorScheme,
  stacked,
  showLegend,
  xAxisLabel,
  yAxisLabel,
  className,
}: BarRendererProps) {
  const scheme = getCategoricalScheme(colorScheme);
  return (
    <div style={{ width, height }} className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={CHART_DEFAULT_MARGIN}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_COLOR} />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fontFamily: CHART_FONT_FAMILY, fill: CHART_AXIS_COLOR }}
            label={
              xAxisLabel
                ? { value: xAxisLabel, position: 'bottom', fill: CHART_AXIS_COLOR }
                : undefined
            }
          />
          <YAxis
            tick={{ fontSize: 12, fontFamily: CHART_FONT_FAMILY, fill: CHART_AXIS_COLOR }}
            label={
              yAxisLabel
                ? { value: yAxisLabel, angle: -90, position: 'insideLeft', fill: CHART_AXIS_COLOR }
                : undefined
            }
          />
          <Tooltip />
          {showLegend && <Legend />}
          {metrics.map((m, i) => (
            <Bar
              key={m}
              dataKey={m}
              fill={nthColor(scheme, i)}
              stackId={stacked ? 'stack' : undefined}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

const transformProps: TransformProps<BarFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<BarFormData>;
  const data = queriesData[0]?.data ?? [];
  const groupby = formData.groupby ?? [];
  const metrics = formData.metrics ?? [];
  const sample = data[0] ?? {};
  const xKey = groupby[0] ?? Object.keys(sample).find((k) => typeof sample[k] !== 'number') ?? Object.keys(sample)[0] ?? '';
  const inferredMetrics = metrics.length
    ? metrics
    : Object.keys(sample).filter((k) => typeof sample[k] === 'number');
  return {
    width,
    height,
    data,
    xKey,
    metrics: inferredMetrics,
    colorScheme: formData.color_scheme ?? 'supersetColors',
    stacked: !!formData.stacked,
    showLegend: formData.show_legend !== false,
    xAxisLabel: formData.x_axis_label,
    yAxisLabel: formData.y_axis_label,
  };
};

const metadata = new ChartMetadata({
  name: 'Bar Chart',
  description:
    'Compare categories with vertical or horizontal bars. Supports stacking and grouping.',
  category: ChartCategory.Ranking,
  tags: ['Featured', 'Categorical', 'Comparison', 'Discrete', 'Ranking'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
  canBeAnnotationTypes: ['EVENT', 'INTERVAL'],
});

export default class BarChartPlugin extends ChartPlugin<BarFormData> {
  constructor() {
    super({ metadata, loadChart: () => BarChartViz, transformProps });
  }
}
