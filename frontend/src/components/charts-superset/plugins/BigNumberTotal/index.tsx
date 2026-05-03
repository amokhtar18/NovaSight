import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { ChartCategory, Behavior } from '../../types/Base';
import { MetricCard } from '@/components/dashboard/MetricCard';

interface BigNumberTotalFormData extends QueryFormData {
  metric?: string;
  subheader?: string;
  prefix?: string;
  suffix?: string;
  format?: 'currency' | 'percentage' | 'number' | 'compact';
}

function BigNumberTotalChart(props: {
  width: number;
  height: number;
  value: number | string;
  subtitle?: string;
  prefix?: string;
  suffix?: string;
  format?: 'currency' | 'percentage' | 'number' | 'compact';
  className?: string;
}) {
  return (
    <div style={{ width: props.width, height: props.height }} className={props.className}>
      <MetricCard
        value={props.value}
        subtitle={props.subtitle}
        prefix={props.prefix}
        suffix={props.suffix}
        format={props.format}
        size="lg"
      />
    </div>
  );
}

const transformProps: TransformProps<BigNumberTotalFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<BigNumberTotalFormData>;
  const data = queriesData[0]?.data ?? [];
  const firstRow = data[0] ?? {};
  const metric = formData.metric ?? Object.keys(firstRow)[0] ?? 'value';
  return {
    width,
    height,
    value: (firstRow[metric] ?? 0) as number | string,
    subtitle: formData.subheader,
    prefix: formData.prefix,
    suffix: formData.suffix,
    format: formData.format,
  };
};

const metadata = new ChartMetadata({
  name: 'Big Number',
  description: 'Displays a single aggregate value, ideal for KPIs.',
  category: ChartCategory.KPI,
  tags: ['Featured', 'Single Value', 'KPI'],
  thumbnail: '',
  behaviors: [Behavior.DrillToDetail],
});

export default class BigNumberTotalChartPlugin extends ChartPlugin<BigNumberTotalFormData> {
  constructor() {
    super({ metadata, loadChart: () => BigNumberTotalChart, transformProps });
  }
}
