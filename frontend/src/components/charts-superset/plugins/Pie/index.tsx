import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Label,
} from 'recharts';
import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { ChartCategory, Behavior } from '../../types/Base';
import { getCategoricalScheme, nthColor } from '../../styling/colorSchemes';

interface PieFormData extends QueryFormData {
  groupby?: string[];
  metric?: string;
  color_scheme?: string;
  show_legend?: boolean;
  donut?: boolean;
  inner_radius?: number;
  show_labels?: boolean;
}

function PieChartViz(props: {
  width: number;
  height: number;
  data: Record<string, unknown>[];
  nameKey: string;
  valueKey: string;
  colorScheme: string;
  showLegend: boolean;
  donut: boolean;
  innerRadius: number;
  showLabels: boolean;
  className?: string;
}) {
  const { width, height, data, nameKey, valueKey, colorScheme, showLegend, donut, innerRadius, showLabels, className } = props;
  const scheme = getCategoricalScheme(colorScheme);
  const radius = Math.min(width, height) / 2 - 20;
  return (
    <div style={{ width, height }} className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            outerRadius={Math.max(radius, 40)}
            innerRadius={donut ? Math.max(radius * (innerRadius / 100), 0) : 0}
            label={showLabels}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={nthColor(scheme, i)} />
            ))}
            {donut && <Label position="center" />}
          </Pie>
          <Tooltip />
          {showLegend && <Legend />}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

const transformProps: TransformProps<PieFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<PieFormData>;
  const data = queriesData[0]?.data ?? [];
  const sample = data[0] ?? {};
  const nameKey =
    formData.groupby?.[0] ??
    Object.keys(sample).find((k) => typeof sample[k] !== 'number') ??
    Object.keys(sample)[0] ??
    '';
  const valueKey =
    formData.metric ??
    Object.keys(sample).find((k) => typeof sample[k] === 'number') ??
    '';
  return {
    width,
    height,
    data,
    nameKey,
    valueKey,
    colorScheme: formData.color_scheme ?? 'supersetColors',
    showLegend: formData.show_legend !== false,
    donut: !!formData.donut,
    innerRadius: formData.inner_radius ?? 50,
    showLabels: formData.show_labels !== false,
  };
};

const metadata = new ChartMetadata({
  name: 'Pie Chart',
  description: 'Compares the contribution each category makes to a whole.',
  category: ChartCategory.Part,
  tags: ['Featured', 'Categorical', 'Percentages', 'Aesthetic'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
});

export default class PieChartPlugin extends ChartPlugin<PieFormData> {
  constructor() {
    super({ metadata, loadChart: () => PieChartViz, transformProps });
  }
}
