import ReactECharts from 'echarts-for-react';
import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { Behavior, ChartCategory } from '../../types/Base';
import { getSequentialScheme } from '../../styling/sequentialSchemes';
import {
  BASE_ANIMATION,
  ECHARTS_STYLE,
  baseAxisStyle,
  baseTextStyle,
  baseTooltip,
} from '../../styling/echarts';

interface HeatmapFormData extends QueryFormData {
  groupby?: string[];
  metric?: string;
  color_scheme?: string;
  linear_color_scheme?: string;
  show_values?: boolean;
}

interface HeatmapDatum {
  x: string;
  y: string;
  v: number;
}

function HeatmapChart(props: {
  width: number;
  height: number;
  xKeys: string[];
  yKeys: string[];
  data: [number, number, number][];
  min: number;
  max: number;
  colors: string[];
  showValues: boolean;
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, xKeys, yKeys, data, min, max, colors, showValues, isDark, className } = props;

  const option = {
    ...BASE_ANIMATION,
    textStyle: baseTextStyle(isDark),
    tooltip: {
      ...baseTooltip(isDark),
      position: 'top' as const,
      formatter: (p: any) =>
        `<strong>${xKeys[p.value[0]]}</strong> × <strong>${yKeys[p.value[1]]}</strong><br/>${p.value[2]}`,
    },
    grid: { left: 56, right: 24, top: 24, bottom: 56, containLabel: true },
    xAxis: { type: 'category' as const, data: xKeys, splitArea: { show: true }, ...baseAxisStyle(isDark) },
    yAxis: { type: 'category' as const, data: yKeys, splitArea: { show: true }, ...baseAxisStyle(isDark) },
    visualMap: {
      min,
      max,
      calculable: true,
      orient: 'horizontal' as const,
      left: 'center',
      bottom: 0,
      inRange: { color: colors },
      textStyle: baseTextStyle(isDark),
    },
    series: [
      {
        type: 'heatmap' as const,
        data,
        label: { show: showValues, fontSize: 10 },
        emphasis: {
          itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.4)' },
        },
      },
    ],
  };

  return (
    <div style={{ width, height }} className={className}>
      <ReactECharts option={option} style={ECHARTS_STYLE} notMerge lazyUpdate />
    </div>
  );
}

const transformProps: TransformProps<HeatmapFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<HeatmapFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const sample = rows[0] ?? {};
  const groupby = formData.groupby ?? [];
  const xField = groupby[0] ?? Object.keys(sample)[0] ?? '';
  const yField = groupby[1] ?? Object.keys(sample)[1] ?? xField;
  const metric =
    formData.metric ??
    Object.keys(sample).find((k) => typeof sample[k] === 'number') ??
    'value';

  const xKeys: string[] = [];
  const yKeys: string[] = [];
  const points: HeatmapDatum[] = [];
  for (const row of rows) {
    const x = String(row[xField] ?? '');
    const y = String(row[yField] ?? '');
    const v = Number(row[metric] ?? 0);
    if (!xKeys.includes(x)) xKeys.push(x);
    if (!yKeys.includes(y)) yKeys.push(y);
    points.push({ x, y, v });
  }
  const data: [number, number, number][] = points.map((p) => [
    xKeys.indexOf(p.x),
    yKeys.indexOf(p.y),
    p.v,
  ]);
  const min = points.length ? Math.min(...points.map((p) => p.v)) : 0;
  const max = points.length ? Math.max(...points.map((p) => p.v)) : 1;

  const seq = getSequentialScheme(formData.linear_color_scheme);
  const colors = seq.colors;

  return {
    width,
    height,
    xKeys,
    yKeys,
    data,
    min,
    max,
    colors,
    showValues: !!formData.show_values,
  };
};

const metadata = new ChartMetadata({
  name: 'Heatmap',
  description: 'Density across two dimensions encoded by color.',
  category: ChartCategory.Correlation,
  tags: ['Comparison', 'Correlation', 'Density'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail],
});

export default class HeatmapChartPlugin extends ChartPlugin<HeatmapFormData> {
  constructor() {
    super({ metadata, loadChart: () => HeatmapChart, transformProps });
  }
}
