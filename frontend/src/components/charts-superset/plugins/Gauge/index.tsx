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
  baseTextStyle,
  baseTooltip,
} from '../../styling/echarts';

interface GaugeFormData extends QueryFormData {
  metric?: string;
  min_value?: number;
  max_value?: number;
  color_scheme?: string;
  unit?: string;
}

function GaugeChart(props: {
  width: number;
  height: number;
  value: number;
  min: number;
  max: number;
  unit?: string;
  colors: string[];
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, value, min, max, unit, colors, isDark, className } = props;
  const option = {
    ...BASE_ANIMATION,
    textStyle: baseTextStyle(isDark),
    tooltip: { ...baseTooltip(isDark), formatter: '{b}: {c}' + (unit ? ` ${unit}` : '') },
    series: [
      {
        type: 'gauge' as const,
        min,
        max,
        startAngle: 200,
        endAngle: -20,
        progress: { show: true, width: 18, itemStyle: { color: colors[0] } },
        axisLine: { lineStyle: { width: 18, color: [[1, 'rgba(0,0,0,0.08)']] } },
        axisTick: { distance: -22, length: 6, lineStyle: { color: baseTextStyle(isDark).color } },
        splitLine: { distance: -28, length: 12, lineStyle: { color: baseTextStyle(isDark).color, width: 2 } },
        axisLabel: { distance: -32, fontSize: 11, color: baseTextStyle(isDark).color },
        anchor: { show: true, size: 14, itemStyle: { color: colors[0] } },
        pointer: { itemStyle: { color: colors[0] } },
        title: { offsetCenter: [0, '85%'], fontSize: 12, color: baseTextStyle(isDark).color },
        detail: {
          valueAnimation: true,
          fontSize: 28,
          offsetCenter: [0, '60%'],
          color: baseTextStyle(isDark).color,
          formatter: (v: number) => `${Math.round(v * 100) / 100}${unit ? ` ${unit}` : ''}`,
        },
        data: [{ value }],
      },
    ],
  };
  return (
    <div style={{ width, height }} className={className}>
      <ReactECharts option={option} style={ECHARTS_STYLE} notMerge lazyUpdate />
    </div>
  );
}

const transformProps: TransformProps<GaugeFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<GaugeFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const firstRow = rows[0] ?? {};
  const metric =
    formData.metric ??
    Object.keys(firstRow).find((k) => typeof firstRow[k] === 'number') ??
    Object.keys(firstRow)[0] ??
    'value';
  const value = Number(firstRow[metric] ?? 0);
  const min = formData.min_value ?? 0;
  const max =
    formData.max_value ??
    (Number.isFinite(value) && value > 0 ? Math.ceil(value * 1.25) : 100);
  return {
    width,
    height,
    value,
    min,
    max,
    unit: formData.unit,
    colors: getCategoricalScheme(formData.color_scheme).colors,
  };
};

const metadata = new ChartMetadata({
  name: 'Gauge Chart',
  description: 'Single value displayed against a range.',
  category: ChartCategory.KPI,
  tags: ['Single Value', 'Aesthetic'],
  thumbnail: '',
});

export default class GaugeChartPlugin extends ChartPlugin<GaugeFormData> {
  constructor() {
    super({ metadata, loadChart: () => GaugeChart, transformProps });
  }
}
