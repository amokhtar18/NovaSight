import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { ChartCategory, Behavior } from '../../types/Base';
import { MetricCard } from '@/components/dashboard/MetricCard';

interface BigNumberFormData extends QueryFormData {
  metric?: string;
  subheader?: string;
  prefix?: string;
  suffix?: string;
  format?: 'currency' | 'percentage' | 'number' | 'compact';
}

interface BigNumberProps {
  width: number;
  height: number;
  value: number | string;
  title?: string;
  subtitle?: string;
  prefix?: string;
  suffix?: string;
  format?: 'currency' | 'percentage' | 'number' | 'compact';
  className?: string;
}

function BigNumberChart({
  width,
  height,
  value,
  title,
  subtitle,
  prefix,
  suffix,
  format,
  className,
}: BigNumberProps) {
  return (
    <div style={{ width, height }} className={className}>
      <MetricCard
        title={title}
        value={value}
        subtitle={subtitle}
        prefix={prefix}
        suffix={suffix}
        format={format}
        size="lg"
      />
    </div>
  );
}

const transformProps: TransformProps<BigNumberFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<BigNumberFormData>;
  const data = queriesData[0]?.data ?? [];
  const firstRow = data[0] ?? {};
  const metric = formData.metric ?? Object.keys(firstRow)[0] ?? 'value';
  const value = (firstRow[metric] ?? 0) as number | string;

  return {
    width,
    height,
    value,
    title: undefined,
    subtitle: formData.subheader,
    prefix: formData.prefix,
    suffix: formData.suffix,
    format: formData.format,
  };
};

const metadata = new ChartMetadata({
  name: 'Big Number',
  description:
    'Showcases a single number, optionally with a label and trend over time.',
  category: ChartCategory.KPI,
  tags: ['Featured', 'Single Value', 'KPI', 'Report'],
  thumbnail: '',
  behaviors: [Behavior.DrillToDetail],
});

export default class BigNumberChartPlugin extends ChartPlugin<BigNumberFormData> {
  constructor() {
    super({
      metadata,
      loadChart: () => BigNumberChart,
      transformProps,
    });
  }
}
