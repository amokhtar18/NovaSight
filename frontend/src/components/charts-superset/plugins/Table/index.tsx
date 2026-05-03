import { ChartMetadata } from '../../models/ChartMetadata';
import { ChartPlugin } from '../../models/ChartPlugin';
import type { ChartProps, QueryFormData } from '../../models/ChartProps';
import type { TransformProps } from '../../models/TransformProps';
import { ChartCategory, Behavior } from '../../types/Base';
import { DataTable } from '@/components/charts/DataTable';
import type { ChartDataColumn } from '@/components/charts/types';

interface TableFormData extends QueryFormData {
  page_size?: number;
  table_title?: string;
}

function TableChart({
  width,
  height,
  data,
  columns,
  pageSize,
  title,
  className,
}: {
  width: number;
  height: number;
  data: Record<string, unknown>[];
  columns: ChartDataColumn[];
  pageSize?: number;
  title?: string;
  className?: string;
}) {
  return (
    <div style={{ width, height, overflow: 'auto' }} className={className}>
      <DataTable
        data={data}
        columns={columns}
        pageSize={pageSize ?? 25}
        title={title}
      />
    </div>
  );
}

function inferColumns(rows: Record<string, unknown>[]): ChartDataColumn[] {
  const sample = rows[0];
  if (!sample) return [];
  return Object.keys(sample).map((name): ChartDataColumn => {
    const v = sample[name];
    let type: ChartDataColumn['type'] = 'string';
    if (typeof v === 'number') type = 'number';
    else if (typeof v === 'boolean') type = 'boolean';
    else if (typeof v === 'string' && !Number.isNaN(Date.parse(v))) {
      type = /\d{4}-\d{2}-\d{2}/.test(v) ? 'datetime' : 'string';
    }
    return { name, type };
  });
}

const transformProps: TransformProps<TableFormData> = (chartProps) => {
  const { width, height, formData, queriesData } = chartProps as ChartProps<TableFormData>;
  const result = queriesData[0];
  const data = result?.data ?? [];
  const columns: ChartDataColumn[] = result?.columns ?? inferColumns(data);
  return {
    width,
    height,
    data,
    columns,
    pageSize: formData.page_size,
    title: formData.table_title,
  };
};

const metadata = new ChartMetadata({
  name: 'Table',
  description:
    'Classic data table — display rows of records with sorting, pagination, and search.',
  category: ChartCategory.Table,
  tags: ['Featured', 'Tabular', 'Report', 'Pagination'],
  thumbnail: '',
  canBeAnnotationTypes: ['EVENT', 'INTERVAL'],
  behaviors: [Behavior.InteractiveChart, Behavior.DrillToDetail, Behavior.DrillBy],
});

export default class TableChartPlugin extends ChartPlugin<TableFormData> {
  constructor() {
    super({ metadata, loadChart: () => TableChart, transformProps });
  }
}
