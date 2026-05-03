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
  baseAxisStyle,
  baseTextStyle,
  baseTooltip,
} from '../../styling/echarts';

interface BoxPlotFormData extends QueryFormData {
  groupby?: string[];
  metric?: string;
  color_scheme?: string;
}

function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return 0;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
}

function boxStats(values: number[]): {
  box: [number, number, number, number, number];
  outliers: number[];
} {
  const sorted = [...values].sort((a, b) => a - b);
  const q1 = quantile(sorted, 0.25);
  const med = quantile(sorted, 0.5);
  const q3 = quantile(sorted, 0.75);
  const iqr = q3 - q1;
  const lo = q1 - 1.5 * iqr;
  const hi = q3 + 1.5 * iqr;
  const inliers = sorted.filter((v) => v >= lo && v <= hi);
  const outliers = sorted.filter((v) => v < lo || v > hi);
  const min = inliers.length ? inliers[0] : sorted[0] ?? 0;
  const max = inliers.length ? inliers[inliers.length - 1] : sorted[sorted.length - 1] ?? 0;
  return { box: [min, q1, med, q3, max], outliers };
}

function BoxPlotChart(props: {
  width: number;
  height: number;
  categories: string[];
  boxData: number[][];
  outliers: [number, number][];
  colors: string[];
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, categories, boxData, outliers, colors, isDark, className } = props;
  const option = {
    ...BASE_ANIMATION,
    color: colors,
    textStyle: baseTextStyle(isDark),
    tooltip: { ...baseTooltip(isDark), trigger: 'item' as const },
    grid: { left: 56, right: 24, top: 24, bottom: 48, containLabel: true },
    xAxis: { type: 'category' as const, data: categories, ...baseAxisStyle(isDark) },
    yAxis: { type: 'value' as const, ...baseAxisStyle(isDark) },
    series: [
      {
        name: 'box',
        type: 'boxplot' as const,
        data: boxData,
        itemStyle: { color: colors[0], borderColor: colors[1] ?? colors[0] },
      },
      {
        name: 'outliers',
        type: 'scatter' as const,
        data: outliers,
        symbolSize: 6,
        itemStyle: { color: colors[2] ?? colors[0] },
      },
    ],
  };
  return (
    <div style={{ width, height }} className={className}>
      <ReactECharts option={option} style={ECHARTS_STYLE} notMerge lazyUpdate />
    </div>
  );
}

const transformProps: TransformProps<BoxPlotFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<BoxPlotFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const sample = rows[0] ?? {};
  const groupKey =
    formData.groupby?.[0] ??
    Object.keys(sample).find((k) => typeof sample[k] !== 'number') ??
    Object.keys(sample)[0] ??
    '';
  const metric =
    formData.metric ??
    Object.keys(sample).find((k) => typeof sample[k] === 'number') ??
    'value';

  const buckets = new Map<string, number[]>();
  for (const row of rows) {
    const k = String(row[groupKey] ?? '');
    const v = Number(row[metric] ?? NaN);
    if (!Number.isFinite(v)) continue;
    const arr = buckets.get(k) ?? [];
    arr.push(v);
    buckets.set(k, arr);
  }
  const categories = Array.from(buckets.keys());
  const boxData: number[][] = [];
  const outliers: [number, number][] = [];
  categories.forEach((cat, i) => {
    const stats = boxStats(buckets.get(cat) ?? []);
    boxData.push(stats.box as unknown as number[]);
    for (const o of stats.outliers) outliers.push([i, o]);
  });
  return {
    width,
    height,
    categories,
    boxData,
    outliers,
    colors: getCategoricalScheme(formData.color_scheme).colors,
  };
};

const metadata = new ChartMetadata({
  name: 'Box Plot',
  description: 'Median, quartiles and outliers across categories.',
  category: ChartCategory.Distribution,
  tags: ['Statistical', 'Distribution', 'Comparison'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart],
});

export default class BoxPlotChartPlugin extends ChartPlugin<BoxPlotFormData> {
  constructor() {
    super({ metadata, loadChart: () => BoxPlotChart, transformProps });
  }
}
