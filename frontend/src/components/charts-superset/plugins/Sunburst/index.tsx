import ReactECharts from 'echarts-for-react';
// Sunburst chart, ECharts-backed.
import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { Behavior, ChartCategory } from '../../types/Base';
import { getCategoricalScheme } from '../../styling/colorSchemes';
import {
  BASE_ANIMATION,
  ECHARTS_STYLE,
  baseTextStyle,
  baseTooltip,
} from '../../styling/echarts';

interface SunburstFormData extends QueryFormData {
  groupby?: string[];
  metric?: string;
  color_scheme?: string;
  show_labels?: boolean;
}

interface SunburstNode {
  name: string;
  value?: number;
  children?: SunburstNode[];
}

function SunburstChart(props: {
  width: number;
  height: number;
  data: SunburstNode[];
  colors: string[];
  showLabels: boolean;
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, data, colors, showLabels, isDark, className } = props;
  const option = {
    ...BASE_ANIMATION,
    color: colors,
    textStyle: baseTextStyle(isDark),
    tooltip: {
      ...baseTooltip(isDark),
      formatter: (p: any) => `${p.treePathInfo.map((n: any) => n.name).filter(Boolean).join(' / ')}<br/><strong>${p.value}</strong>`,
    },
    series: [
      {
        type: 'sunburst' as const,
        radius: ['10%', '95%'],
        data,
        emphasis: { focus: 'ancestor' as const },
        label: { show: showLabels, fontSize: 11 },
        levels: [
          {},
          { r0: '15%', r: '40%', label: { rotate: 'tangential' as const } },
          { r0: '40%', r: '70%', label: { align: 'right' as const } },
          { r0: '70%', r: '95%', label: { position: 'outside' as const, padding: 3, silent: false }, itemStyle: { borderWidth: 3 } },
        ],
      },
    ],
  };
  return (
    <div style={{ width, height }} className={className}>
      <ReactECharts option={option} style={ECHARTS_STYLE} notMerge lazyUpdate />
    </div>
  );
}

function buildHierarchy(
  rows: Record<string, unknown>[],
  groupby: string[],
  metric: string,
): SunburstNode[] {
  const root: SunburstNode = { name: 'root', children: [] };
  for (const row of rows) {
    let cursor = root;
    for (const dim of groupby) {
      const name = String(row[dim] ?? '∅');
      cursor.children = cursor.children ?? [];
      let child = cursor.children.find((c) => c.name === name);
      if (!child) {
        child = { name, children: [] };
        cursor.children.push(child);
      }
      cursor = child;
    }
    cursor.value = (cursor.value ?? 0) + Number(row[metric] ?? 0);
  }
  // Drop empty children arrays on leaves.
  const prune = (n: SunburstNode) => {
    if (n.children) {
      if (n.children.length === 0) delete n.children;
      else n.children.forEach(prune);
    }
  };
  (root.children ?? []).forEach(prune);
  return root.children ?? [];
}

const transformProps: TransformProps<SunburstFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<SunburstFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const sample = rows[0] ?? {};
  const groupby = formData.groupby?.length
    ? formData.groupby
    : Object.keys(sample).filter((k) => typeof sample[k] !== 'number').slice(0, 3);
  const metric =
    formData.metric ??
    Object.keys(sample).find((k) => typeof sample[k] === 'number') ??
    'value';
  const data = buildHierarchy(rows, groupby, metric);
  const scheme = getCategoricalScheme(formData.color_scheme);
  return {
    width,
    height,
    data,
    colors: scheme.colors,
    showLabels: formData.show_labels !== false,
  };
};

const metadata = new ChartMetadata({
  name: 'Sunburst Chart',
  description: 'Hierarchical contribution as concentric rings.',
  category: ChartCategory.Part,
  tags: ['Hierarchy', 'Aesthetic', 'Categorical'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
});

export default class SunburstChartPlugin extends ChartPlugin<SunburstFormData> {
  constructor() {
    super({ metadata, loadChart: () => SunburstChart, transformProps });
  }
}
