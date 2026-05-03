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
  baseTextStyle,
  baseTooltip,
} from '../../styling/echarts';

interface TreemapFormData extends QueryFormData {
  groupby?: string[];
  metric?: string;
  color_scheme?: string;
}

interface TreemapNode {
  name: string;
  value?: number;
  children?: TreemapNode[];
}

function TreemapChart(props: {
  width: number;
  height: number;
  data: TreemapNode[];
  colors: string[];
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, data, colors, isDark, className } = props;
  const option = {
    ...BASE_ANIMATION,
    color: colors,
    textStyle: baseTextStyle(isDark),
    tooltip: {
      ...baseTooltip(isDark),
      formatter: (p: any) =>
        `${p.treePathInfo.map((n: any) => n.name).filter(Boolean).join(' / ')}<br/><strong>${p.value}</strong>`,
    },
    series: [
      {
        type: 'treemap' as const,
        data,
        roam: false,
        nodeClick: 'zoomToNode' as const,
        breadcrumb: { show: true, bottom: 0 },
        label: {
          show: true,
          fontFamily: baseTextStyle(isDark).fontFamily,
          fontSize: 12,
        },
        upperLabel: { show: true, height: 24 },
        levels: [
          { itemStyle: { borderColor: '#fff', borderWidth: 2, gapWidth: 2 } },
          { colorSaturation: [0.35, 0.6], itemStyle: { borderColorSaturation: 0.7, gapWidth: 1, borderWidth: 1 } },
          { colorSaturation: [0.35, 0.5], itemStyle: { borderColorSaturation: 0.6, gapWidth: 1 } },
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
): TreemapNode[] {
  const root: TreemapNode = { name: 'root', children: [] };
  for (const row of rows) {
    let cursor = root;
    for (const dim of groupby) {
      const name = String(row[dim] ?? '∅');
      cursor.children = cursor.children ?? [];
      let child = cursor.children.find((c) => c.name === name);
      if (!child) {
        child = { name };
        cursor.children.push(child);
      }
      cursor = child;
    }
    cursor.value = (cursor.value ?? 0) + Number(row[metric] ?? 0);
  }
  return root.children ?? [];
}

const transformProps: TransformProps<TreemapFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<TreemapFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const sample = rows[0] ?? {};
  const groupby = formData.groupby?.length
    ? formData.groupby
    : Object.keys(sample).filter((k) => typeof sample[k] !== 'number').slice(0, 2);
  const metric =
    formData.metric ??
    Object.keys(sample).find((k) => typeof sample[k] === 'number') ??
    'value';
  const data = buildHierarchy(rows, groupby, metric);
  return {
    width,
    height,
    data,
    colors: getCategoricalScheme(formData.color_scheme).colors,
  };
};

const metadata = new ChartMetadata({
  name: 'Treemap',
  description: 'Hierarchical contribution as nested rectangles.',
  category: ChartCategory.Part,
  tags: ['Hierarchy', 'Categorical', 'Density'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
});

export default class TreemapChartPlugin extends ChartPlugin<TreemapFormData> {
  constructor() {
    super({ metadata, loadChart: () => TreemapChart, transformProps });
  }
}
