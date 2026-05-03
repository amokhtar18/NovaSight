import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
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

interface ScatterFormData extends QueryFormData {
  x?: string;
  y?: string;
  size?: string;
  color_scheme?: string;
  show_legend?: boolean;
}

function ScatterChartViz(props: {
  width: number;
  height: number;
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  sizeKey?: string;
  colorScheme: string;
  showLegend: boolean;
  className?: string;
}) {
  const { width, height, data, xKey, yKey, sizeKey, colorScheme, showLegend, className } = props;
  const scheme = getCategoricalScheme(colorScheme);
  return (
    <div style={{ width, height }} className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 16, right: 24, bottom: 36, left: 48 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} type="number" name={xKey} />
          <YAxis dataKey={yKey} type="number" name={yKey} />
          {sizeKey && <ZAxis dataKey={sizeKey} range={[40, 400]} name={sizeKey} />}
          <Tooltip cursor={{ strokeDasharray: '3 3' }} />
          {showLegend && <Legend />}
          <Scatter name={yKey} data={data} fill={nthColor(scheme, 0)} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

const transformProps: TransformProps<ScatterFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<ScatterFormData>;
  const data = queriesData[0]?.data ?? [];
  const sample = data[0] ?? {};
  const numericKeys = Object.keys(sample).filter((k) => typeof sample[k] === 'number');
  return {
    width,
    height,
    data,
    xKey: formData.x ?? numericKeys[0] ?? '',
    yKey: formData.y ?? numericKeys[1] ?? numericKeys[0] ?? '',
    sizeKey: formData.size,
    colorScheme: formData.color_scheme ?? 'supersetColors',
    showLegend: formData.show_legend !== false,
  };
};

const metadata = new ChartMetadata({
  name: 'Scatter Plot',
  description: 'Plot the relationship between two numeric variables.',
  category: ChartCategory.Correlation,
  tags: ['Correlation', 'Comparison', 'Multi-Variates', 'Numeric'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart],
});

export default class ScatterChartPlugin extends ChartPlugin<ScatterFormData> {
  constructor() {
    super({ metadata, loadChart: () => ScatterChartViz, transformProps });
  }
}
