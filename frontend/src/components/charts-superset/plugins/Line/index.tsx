import {
  LineChart,
  Line,
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

interface LineFormData extends QueryFormData {
  groupby?: string[];
  metrics?: string[];
  color_scheme?: string;
  show_legend?: boolean;
  smooth?: boolean;
  show_markers?: boolean;
  x_axis?: string;
}

function LineChartViz(props: {
  width: number;
  height: number;
  data: Record<string, unknown>[];
  xKey: string;
  metrics: string[];
  colorScheme: string;
  smooth: boolean;
  showLegend: boolean;
  showMarkers: boolean;
  className?: string;
}) {
  const { width, height, data, xKey, metrics, colorScheme, smooth, showLegend, showMarkers, className } = props;
  const scheme = getCategoricalScheme(colorScheme);
  return (
    <div style={{ width, height }} className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={CHART_DEFAULT_MARGIN}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_COLOR} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12, fontFamily: CHART_FONT_FAMILY, fill: CHART_AXIS_COLOR }} />
          <YAxis tick={{ fontSize: 12, fontFamily: CHART_FONT_FAMILY, fill: CHART_AXIS_COLOR }} />
          <Tooltip />
          {showLegend && <Legend />}
          {metrics.map((m, i) => (
            <Line
              key={m}
              type={smooth ? 'monotone' : 'linear'}
              dataKey={m}
              stroke={nthColor(scheme, i)}
              strokeWidth={2}
              dot={showMarkers ? { r: 3 } : false}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

const transformProps: TransformProps<LineFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<LineFormData>;
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
    smooth: formData.smooth !== false,
    showLegend: formData.show_legend !== false,
    showMarkers: !!formData.show_markers,
  };
};

const metadata = new ChartMetadata({
  name: 'Line Chart',
  description: 'Track values over a continuous axis (typically time).',
  category: ChartCategory.Evolution,
  tags: ['Featured', 'Time-series', 'Continuous', 'Trend', 'Line'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
  canBeAnnotationTypes: ['EVENT', 'INTERVAL', 'TIME_SERIES', 'FORMULA'],
});

export default class LineChartPlugin extends ChartPlugin<LineFormData> {
  constructor() {
    super({ metadata, loadChart: () => LineChartViz, transformProps });
  }
}
