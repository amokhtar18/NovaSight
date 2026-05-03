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

interface SankeyFormData extends QueryFormData {
  source?: string;
  target?: string;
  metric?: string;
  color_scheme?: string;
}

interface SankeyNode {
  name: string;
}
interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

function SankeyChart(props: {
  width: number;
  height: number;
  nodes: SankeyNode[];
  links: SankeyLink[];
  colors: string[];
  isDark?: boolean;
  className?: string;
}) {
  const { width, height, nodes, links, colors, isDark, className } = props;
  const option = {
    ...BASE_ANIMATION,
    color: colors,
    textStyle: baseTextStyle(isDark),
    tooltip: { ...baseTooltip(isDark), trigger: 'item' as const },
    series: [
      {
        type: 'sankey' as const,
        data: nodes,
        links,
        emphasis: { focus: 'adjacency' as const },
        lineStyle: { color: 'gradient', curveness: 0.5 },
        label: { color: baseTextStyle(isDark).color, fontFamily: baseTextStyle(isDark).fontFamily },
        nodeAlign: 'justify' as const,
      },
    ],
  };
  return (
    <div style={{ width, height }} className={className}>
      <ReactECharts option={option} style={ECHARTS_STYLE} notMerge lazyUpdate />
    </div>
  );
}

const transformProps: TransformProps<SankeyFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<SankeyFormData>;
  const rows = (queriesData[0]?.data ?? []) as Record<string, unknown>[];
  const sample = rows[0] ?? {};
  const stringKeys = Object.keys(sample).filter((k) => typeof sample[k] !== 'number');
  const numericKeys = Object.keys(sample).filter((k) => typeof sample[k] === 'number');
  const source = formData.source ?? stringKeys[0] ?? '';
  const target = formData.target ?? stringKeys[1] ?? stringKeys[0] ?? '';
  const metric = formData.metric ?? numericKeys[0] ?? 'value';

  const nameSet = new Set<string>();
  const links: SankeyLink[] = [];
  for (const row of rows) {
    const s = String(row[source] ?? '');
    const t = String(row[target] ?? '');
    const v = Number(row[metric] ?? 0);
    if (!s || !t || !Number.isFinite(v) || v <= 0) continue;
    nameSet.add(s);
    nameSet.add(t);
    links.push({ source: s, target: t, value: v });
  }
  const nodes: SankeyNode[] = Array.from(nameSet).map((name) => ({ name }));
  return {
    width,
    height,
    nodes,
    links,
    colors: getCategoricalScheme(formData.color_scheme).colors,
  };
};

const metadata = new ChartMetadata({
  name: 'Sankey Diagram',
  description: 'Visualise flow between nodes via weighted links.',
  category: ChartCategory.Flow,
  tags: ['Relational', 'Multi-Variates'],
  thumbnail: '',
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
});

export default class SankeyChartPlugin extends ChartPlugin<SankeyFormData> {
  constructor() {
    super({ metadata, loadChart: () => SankeyChart, transformProps });
  }
}
