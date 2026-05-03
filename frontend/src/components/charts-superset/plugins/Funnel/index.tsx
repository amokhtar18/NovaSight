import ReactECharts from 'echarts-for-react';
import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { Behavior, ChartCategory } from '../../types/Base';
import { getCategoricalScheme } from '../../styling/colorSchemes';
import {
  BASE_ANIMATION,
  ECHARTS_STYLE,
  baseLegend,
  baseTextStyle,
  baseTooltip,
} from '../../styling/echarts';

interface FunnelFormData extends QueryFormData {
  groupby?: string[];
  metric?: string;
  color_scheme?: string;
  show_legend?: boolean;
}

function FunnelChart(props: {
  width: number;
  height: number;
  data: { name: string; value: number }[];
  colors: string[];
  showLegend: boolean;
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, data, colors, showLegend, isDark, className } = props;
  const option = {
    ...BASE_ANIMATION,
    color: colors,
    textStyle: baseTextStyle(isDark),
    tooltip: { ...baseTooltip(isDark), trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    legend: showLegend ? { ...baseLegend(isDark), data: data.map((d) => d.name) } : undefined,
    series: [
      {
        type: 'funnel' as const,
        data,
        sort: 'descending' as const,
        gap: 2,
        label: { show: true, position: 'inside' as const, fontFamily: baseTextStyle(isDark).fontFamily },
        labelLine: { length: 10, lineStyle: { width: 1, type: 'solid' as const } },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        emphasis: { label: { fontSize: 14 } },
      },
    ],
  };
  return (
    <div style={{ width, height }} className={className}>
      <ReactECharts option={option} style={ECHARTS_STYLE} notMerge lazyUpdate />
    </div>
  );
}

const transformProps: TransformProps<FunnelFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<FunnelFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const sample = rows[0] ?? {};
  const nameKey =
    formData.groupby?.[0] ??
    Object.keys(sample).find((k) => typeof sample[k] !== 'number') ??
    Object.keys(sample)[0] ??
    '';
  const valueKey =
    formData.metric ??
    Object.keys(sample).find((k) => typeof sample[k] === 'number') ??
    '';
  const data = rows.map((row) => ({
    name: String(row[nameKey] ?? ''),
    value: Number(row[valueKey] ?? 0),
  }));
  return {
    width,
    height,
    data,
    colors: getCategoricalScheme(formData.color_scheme).colors,
    showLegend: formData.show_legend !== false,
  };
};

const metadata = new ChartMetadata({
  name: 'Funnel Chart',
  description: 'Show progression through stages.',
  category: ChartCategory.Part,
  tags: ['Sequential', 'Categorical'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail],
});

export default class FunnelChartPlugin extends ChartPlugin<FunnelFormData> {
  constructor() {
    super({ metadata, loadChart: () => FunnelChart, transformProps });
  }
}
