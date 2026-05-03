import ReactECharts from 'echarts-for-react';
import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { ChartCategory } from '../../types/Base';
import { getCategoricalScheme } from '../../styling/colorSchemes';
import {
  BASE_ANIMATION,
  ECHARTS_STYLE,
  baseLegend,
  baseTextStyle,
  baseTooltip,
} from '../../styling/echarts';

interface RadarFormData extends QueryFormData {
  groupby?: string[];
  metrics?: string[];
  color_scheme?: string;
  show_legend?: boolean;
}

function RadarChart(props: {
  width: number;
  height: number;
  indicators: { name: string; max: number }[];
  series: { name: string; value: number[] }[];
  colors: string[];
  showLegend: boolean;
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, indicators, series, colors, showLegend, isDark, className } = props;
  const option = {
    ...BASE_ANIMATION,
    color: colors,
    textStyle: baseTextStyle(isDark),
    tooltip: { ...baseTooltip(isDark), trigger: 'item' as const },
    legend: showLegend ? { ...baseLegend(isDark), data: series.map((s) => s.name) } : undefined,
    radar: {
      indicator: indicators,
      shape: 'polygon' as const,
      splitNumber: 4,
      axisName: { color: baseTextStyle(isDark).color, fontFamily: baseTextStyle(isDark).fontFamily },
      splitLine: { lineStyle: { color: 'rgba(127, 127, 127, 0.25)' } },
      splitArea: { show: false },
    },
    series: [
      {
        type: 'radar' as const,
        data: series,
        emphasis: { lineStyle: { width: 3 } },
        areaStyle: { opacity: 0.18 },
      },
    ],
  };
  return (
    <div style={{ width, height }} className={className}>
      <ReactECharts option={option} style={ECHARTS_STYLE} notMerge lazyUpdate />
    </div>
  );
}

const transformProps: TransformProps<RadarFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<RadarFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const sample = rows[0] ?? {};
  const groupKey =
    formData.groupby?.[0] ??
    Object.keys(sample).find((k) => typeof sample[k] !== 'number') ??
    Object.keys(sample)[0] ??
    '';
  const metrics = formData.metrics?.length
    ? formData.metrics
    : Object.keys(sample).filter((k) => typeof sample[k] === 'number');

  const maxima: Record<string, number> = {};
  for (const row of rows) {
    for (const m of metrics) {
      const v = Number(row[m] ?? 0);
      if (!Number.isFinite(v)) continue;
      maxima[m] = Math.max(maxima[m] ?? 0, v);
    }
  }
  const indicators = metrics.map((m) => ({
    name: m,
    max: Math.max(maxima[m] ?? 1, 1),
  }));
  const series = rows.map((row) => ({
    name: String(row[groupKey] ?? ''),
    value: metrics.map((m) => Number(row[m] ?? 0)),
  }));
  return {
    width,
    height,
    indicators,
    series,
    colors: getCategoricalScheme(formData.color_scheme).colors,
    showLegend: formData.show_legend !== false,
  };
};

const metadata = new ChartMetadata({
  name: 'Radar Chart',
  description: 'Compare entities across multiple metrics.',
  category: ChartCategory.Ranking,
  tags: ['Multi-Variates', 'Comparison', 'Aesthetic'],
  thumbnail: '',
});

export default class RadarChartPlugin extends ChartPlugin<RadarFormData> {
  constructor() {
    super({ metadata, loadChart: () => RadarChart, transformProps });
  }
}
