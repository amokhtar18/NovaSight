/**
 * DatasetDetailPage
 *
 * Superset-inspired dataset editor. Three tabs:
 *   - Columns: rename, mark groupby/filterable/temporal, hide.
 *   - Metrics: define reusable DAX-style aggregations.
 *   - Preview: sample rows from the underlying ClickHouse table.
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, RefreshCcw, Save, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/components/ui/use-toast';
import {
  useDataset,
  useDatasetPreview,
  useDeleteDataset,
  useReplaceDatasetColumns,
  useReplaceDatasetMetrics,
  useUpdateDataset,
} from '../hooks/useDatasets';
import type { DatasetColumn, DatasetMetric } from '../types';

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const { data: dataset, isLoading } = useDataset(id);
  const updateMut = useUpdateDataset(id ?? '');
  const replaceCols = useReplaceDatasetColumns(id ?? '');
  const replaceMetrics = useReplaceDatasetMetrics(id ?? '');
  const removeMut = useDeleteDataset();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [columns, setColumns] = useState<DatasetColumn[]>([]);
  const [metrics, setMetrics] = useState<DatasetMetric[]>([]);

  useEffect(() => {
    if (!dataset) return;
    setName(dataset.name);
    setDescription(dataset.description ?? '');
    setColumns(dataset.columns ?? []);
    setMetrics(dataset.metrics ?? []);
  }, [dataset]);

  const dirtyMeta =
    !!dataset &&
    (name !== dataset.name || description !== (dataset.description ?? ''));

  const handleSaveMeta = async () => {
    if (!id) return;
    try {
      await updateMut.mutateAsync({ name, description });
      toast({ title: 'Dataset saved' });
    } catch (err) {
      toast({
        title: 'Save failed',
        description: err instanceof Error ? err.message : String(err),
        variant: 'destructive',
      });
    }
  };

  const handleSaveColumns = async () => {
    try {
      await replaceCols.mutateAsync(columns);
      toast({ title: 'Columns updated' });
    } catch (err) {
      toast({
        title: 'Failed to save columns',
        description: err instanceof Error ? err.message : String(err),
        variant: 'destructive',
      });
    }
  };

  const handleSaveMetrics = async () => {
    try {
      await replaceMetrics.mutateAsync(metrics);
      toast({ title: 'Metrics updated' });
    } catch (err) {
      toast({
        title: 'Failed to save metrics',
        description: err instanceof Error ? err.message : String(err),
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!id || !dataset) return;
    if (!window.confirm(`Delete dataset "${dataset.name}"?`)) return;
    await removeMut.mutateAsync({ id });
    toast({ title: 'Dataset deleted' });
    navigate('/datasets');
  };

  if (isLoading || !dataset) {
    return (
      <div className="container mx-auto py-6 space-y-4">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/datasets')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{dataset.name}</h1>
            {dataset.is_managed && (
              <Badge className="bg-blue-500/15 text-blue-600">
                Managed (dbt)
              </Badge>
            )}
            <Badge variant="outline">{dataset.kind}</Badge>
          </div>
          {dataset.table_name && (
            <p className="text-sm text-muted-foreground">
              {[dataset.database_name, dataset.schema, dataset.table_name]
                .filter(Boolean)
                .join('.')}
            </p>
          )}
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={handleDelete}
          disabled={removeMut.isPending}
        >
          <Trash2 className="h-4 w-4 mr-2" />
          Delete
        </Button>
      </div>

      <Card>
        <CardContent className="p-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={dataset.is_managed}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="md:col-span-2 flex justify-end">
            <Button
              size="sm"
              onClick={handleSaveMeta}
              disabled={!dirtyMeta || updateMut.isPending}
            >
              <Save className="h-4 w-4 mr-2" />
              Save details
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="columns">
        <TabsList>
          <TabsTrigger value="columns">
            Columns ({columns.length})
          </TabsTrigger>
          <TabsTrigger value="metrics">
            Metrics ({metrics.length})
          </TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>

        <TabsContent value="columns" className="mt-4">
          <ColumnsEditor
            columns={columns}
            onChange={setColumns}
            onSave={handleSaveColumns}
            saving={replaceCols.isPending}
          />
        </TabsContent>

        <TabsContent value="metrics" className="mt-4">
          <MetricsEditor
            metrics={metrics}
            columns={columns}
            onChange={setMetrics}
            onSave={handleSaveMetrics}
            saving={replaceMetrics.isPending}
          />
        </TabsContent>

        <TabsContent value="preview" className="mt-4">
          <PreviewPane datasetId={id!} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------- Columns ----------

interface ColumnsEditorProps {
  columns: DatasetColumn[];
  onChange: (cols: DatasetColumn[]) => void;
  onSave: () => void;
  saving: boolean;
}

function ColumnsEditor({
  columns,
  onChange,
  onSave,
  saving,
}: ColumnsEditorProps) {
  const update = (idx: number, patch: Partial<DatasetColumn>) => {
    onChange(columns.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Column</TableHead>
                <TableHead>Verbose name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-center">Temporal</TableHead>
                <TableHead className="text-center">Group by</TableHead>
                <TableHead className="text-center">Filterable</TableHead>
                <TableHead className="text-center">Hidden</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {columns.map((c, idx) => (
                <TableRow key={c.column_name}>
                  <TableCell className="font-mono text-xs">
                    {c.column_name}
                  </TableCell>
                  <TableCell>
                    <Input
                      value={c.verbose_name ?? ''}
                      onChange={(e) =>
                        update(idx, { verbose_name: e.target.value })
                      }
                      className="h-8"
                    />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {c.type ?? '—'}
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={c.is_dttm}
                      onCheckedChange={(v) => update(idx, { is_dttm: v })}
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={c.groupby}
                      onCheckedChange={(v) => update(idx, { groupby: v })}
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={c.filterable}
                      onCheckedChange={(v) => update(idx, { filterable: v })}
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={c.is_hidden}
                      onCheckedChange={(v) => update(idx, { is_hidden: v })}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="flex justify-end">
          <Button onClick={onSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            Save columns
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------- Metrics ----------

interface MetricsEditorProps {
  metrics: DatasetMetric[];
  columns: DatasetColumn[];
  onChange: (m: DatasetMetric[]) => void;
  onSave: () => void;
  saving: boolean;
}

type Aggregation =
  | 'SUM'
  | 'AVG'
  | 'COUNT'
  | 'COUNT_DISTINCT'
  | 'MIN'
  | 'MAX'
  | 'MEDIAN'
  | 'CUSTOM';

const AGGREGATIONS: { value: Aggregation; label: string }[] = [
  { value: 'SUM', label: 'Sum' },
  { value: 'AVG', label: 'Average' },
  { value: 'COUNT', label: 'Count' },
  { value: 'COUNT_DISTINCT', label: 'Count distinct' },
  { value: 'MIN', label: 'Min' },
  { value: 'MAX', label: 'Max' },
  { value: 'MEDIAN', label: 'Median' },
  { value: 'CUSTOM', label: 'Custom SQL' },
];

// Aggregations whose target column should be numeric (best-effort UX hint).
const NUMERIC_AGGS: ReadonlySet<Aggregation> = new Set([
  'SUM',
  'AVG',
  'MIN',
  'MAX',
  'MEDIAN',
]);

const FORMAT_PRESETS: { value: string; label: string }[] = [
  { value: '', label: 'Default' },
  { value: ',d', label: 'Number (1,234)' },
  { value: ',.2f', label: 'Decimal (1,234.56)' },
  { value: '$,.2f', label: 'Currency ($1,234.56)' },
  { value: '.1%', label: 'Percent (12.3%)' },
  { value: '.2s', label: 'Compact (1.2k)' },
];

function isNumericColumn(c: DatasetColumn): boolean {
  const t = (c.type ?? '').toLowerCase();
  if (!t) return true; // unknown type — don't filter out
  return /(int|float|double|decimal|numeric|number|long|short|byte|real|money)/.test(
    t,
  );
}

function composeExpression(agg: Aggregation, column: string): string {
  if (agg === 'CUSTOM') return '';
  if (agg === 'COUNT' && (!column || column === '*')) return 'COUNT(*)';
  if (agg === 'COUNT_DISTINCT')
    return column ? `COUNT(DISTINCT ${column})` : 'COUNT(DISTINCT *)';
  return column ? `${agg}(${column})` : `${agg}()`;
}

function parseExpression(
  expr: string,
): { agg: Aggregation; column: string } | null {
  if (!expr) return null;
  const trimmed = expr.trim();
  // COUNT(DISTINCT col)
  const distinct = trimmed.match(/^COUNT\s*\(\s*DISTINCT\s+(.+?)\s*\)$/i);
  if (distinct) return { agg: 'COUNT_DISTINCT', column: distinct[1] };
  // AGG(col)
  const m = trimmed.match(/^([A-Z_]+)\s*\((.*)\)$/i);
  if (m) {
    const aggToken = m[1].toUpperCase();
    const col = m[2].trim();
    const known = AGGREGATIONS.find((a) => a.value === aggToken);
    if (known && known.value !== 'CUSTOM') {
      return { agg: known.value, column: col === '*' ? '' : col };
    }
  }
  return null;
}

function MetricsEditor({
  metrics,
  columns,
  onChange,
  onSave,
  saving,
}: MetricsEditorProps) {
  const update = (idx: number, patch: Partial<DatasetMetric>) => {
    onChange(metrics.map((m, i) => (i === idx ? { ...m, ...patch } : m)));
  };
  const remove = (idx: number) => {
    onChange(metrics.filter((_, i) => i !== idx));
  };
  const add = () => {
    onChange([
      ...metrics,
      {
        metric_name: `metric_${metrics.length + 1}`,
        verbose_name: '',
        expression: 'COUNT(*)',
        metric_type: 'count',
        is_restricted: false,
        is_hidden: false,
      },
    ]);
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        {metrics.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No metrics defined yet. Configure aggregations like
            <code className="mx-1 px-1 bg-muted rounded">SUM(amount)</code>
            so they appear in the chart builder — no SQL required for the
            common cases.
          </p>
        )}

        {metrics.map((m, idx) => (
          <MetricRow
            key={idx}
            metric={m}
            columns={columns}
            onPatch={(patch) => update(idx, patch)}
            onRemove={() => remove(idx)}
          />
        ))}

        <div className="flex justify-between">
          <Button variant="outline" size="sm" onClick={add}>
            + Add metric
          </Button>
          <Button onClick={onSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            Save metrics
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

interface MetricRowProps {
  metric: DatasetMetric;
  columns: DatasetColumn[];
  onPatch: (patch: Partial<DatasetMetric>) => void;
  onRemove: () => void;
}

function MetricRow({ metric, columns, onPatch, onRemove }: MetricRowProps) {
  const parsed = useMemo(() => parseExpression(metric.expression), [
    metric.expression,
  ]);
  // If the expression cannot be parsed into agg+column, treat as custom.
  const initialAgg: Aggregation = parsed?.agg ?? 'CUSTOM';
  const initialCol = parsed?.column ?? '';
  const [agg, setAgg] = useState<Aggregation>(initialAgg);
  const [column, setColumn] = useState<string>(initialCol);
  const [customExpr, setCustomExpr] = useState<string>(
    initialAgg === 'CUSTOM' ? metric.expression : '',
  );
  const isFormatPreset =
    !metric.d3format ||
    FORMAT_PRESETS.some((p) => p.value === metric.d3format);

  // Keep state in sync when external expression changes (e.g. saved/reloaded).
  useEffect(() => {
    const p = parseExpression(metric.expression);
    if (p) {
      setAgg(p.agg);
      setColumn(p.column);
    } else if (metric.expression) {
      setAgg('CUSTOM');
      setCustomExpr(metric.expression);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metric.id]);

  const visibleColumns = useMemo(() => {
    const cols = columns.filter((c) => !c.is_hidden);
    if (NUMERIC_AGGS.has(agg)) {
      const numeric = cols.filter(isNumericColumn);
      // Fall back to all columns if no numeric ones detected.
      return numeric.length ? numeric : cols;
    }
    return cols;
  }, [columns, agg]);

  const aggToMetricType = (a: Aggregation): string => {
    switch (a) {
      case 'SUM':
        return 'sum';
      case 'AVG':
        return 'avg';
      case 'COUNT':
        return 'count';
      case 'COUNT_DISTINCT':
        return 'count_distinct';
      case 'MIN':
        return 'min';
      case 'MAX':
        return 'max';
      case 'MEDIAN':
        return 'median';
      default:
        return 'custom';
    }
  };

  const handleAggChange = (next: Aggregation) => {
    setAgg(next);
    if (next === 'CUSTOM') {
      onPatch({
        expression: customExpr || metric.expression,
        metric_type: 'custom',
      });
    } else {
      const col = next === 'COUNT' ? '' : column;
      onPatch({
        expression: composeExpression(next, col),
        metric_type: aggToMetricType(next),
      });
    }
  };

  const handleColumnChange = (col: string) => {
    setColumn(col);
    if (agg !== 'CUSTOM') {
      onPatch({
        expression: composeExpression(agg, col),
        metric_type: aggToMetricType(agg),
      });
    }
  };

  const handleCustomChange = (val: string) => {
    setCustomExpr(val);
    onPatch({ expression: val, metric_type: 'custom' });
  };

  return (
    <div className="grid gap-3 md:grid-cols-12 items-start border rounded p-3">
      <div className="md:col-span-2">
        <label className="text-xs text-muted-foreground">Name</label>
        <Input
          value={metric.metric_name}
          onChange={(e) => onPatch({ metric_name: e.target.value })}
          className="h-8 font-mono text-xs"
        />
      </div>
      <div className="md:col-span-3">
        <label className="text-xs text-muted-foreground">Label</label>
        <Input
          value={metric.verbose_name ?? ''}
          onChange={(e) => onPatch({ verbose_name: e.target.value })}
          className="h-8"
          placeholder="Total revenue"
        />
      </div>
      <div className="md:col-span-2">
        <label className="text-xs text-muted-foreground">Aggregation</label>
        <Select
          value={agg}
          onValueChange={(v) => handleAggChange(v as Aggregation)}
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {AGGREGATIONS.map((a) => (
              <SelectItem key={a.value} value={a.value}>
                {a.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="md:col-span-2">
        <label className="text-xs text-muted-foreground">Column</label>
        {agg === 'CUSTOM' ? (
          <div className="h-8 flex items-center text-xs text-muted-foreground">
            —
          </div>
        ) : agg === 'COUNT' ? (
          <Select
            value={column || '*'}
            onValueChange={(v) =>
              handleColumnChange(v === '*' ? '' : v)
            }
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="*">* (all rows)</SelectItem>
              {visibleColumns.map((c) => (
                <SelectItem key={c.column_name} value={c.column_name}>
                  {c.column_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Select value={column} onValueChange={handleColumnChange}>
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Choose…" />
            </SelectTrigger>
            <SelectContent>
              {visibleColumns.map((c) => (
                <SelectItem key={c.column_name} value={c.column_name}>
                  {c.column_name}
                  {c.type ? (
                    <span className="text-muted-foreground ml-2">
                      {c.type}
                    </span>
                  ) : null}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      <div className="md:col-span-2">
        <label className="text-xs text-muted-foreground">Format</label>
        <Select
          value={isFormatPreset ? metric.d3format ?? '' : '__custom__'}
          onValueChange={(v) =>
            onPatch({ d3format: v === '__custom__' ? metric.d3format : v })
          }
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FORMAT_PRESETS.map((f) => (
              <SelectItem key={f.label} value={f.value}>
                {f.label}
              </SelectItem>
            ))}
            <SelectItem value="__custom__">Custom…</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="md:col-span-1 flex items-end justify-end h-full">
        <Button variant="ghost" size="icon" onClick={onRemove}>
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {agg === 'CUSTOM' && (
        <div className="md:col-span-12">
          <label className="text-xs text-muted-foreground">
            SQL expression
          </label>
          <Input
            value={customExpr}
            onChange={(e) => handleCustomChange(e.target.value)}
            className="h-8 font-mono text-xs"
            placeholder="SUM(CASE WHEN status='paid' THEN amount END)"
          />
        </div>
      )}
      {!isFormatPreset && (
        <div className="md:col-span-12">
          <label className="text-xs text-muted-foreground">
            Custom d3 format
          </label>
          <Input
            value={metric.d3format ?? ''}
            onChange={(e) => onPatch({ d3format: e.target.value })}
            className="h-8 font-mono text-xs"
            placeholder=",.2f"
          />
        </div>
      )}
      <div className="md:col-span-12 text-xs font-mono text-muted-foreground">
        → <span className="text-foreground">{metric.expression || '—'}</span>
      </div>
    </div>
  );
}

// ---------- Preview ----------

function PreviewPane({ datasetId }: { datasetId: string }) {
  const [limit] = useState(100);
  const { data, isLoading, refetch, isFetching } = useDatasetPreview(
    datasetId,
    limit,
  );

  const cols = data?.columns ?? [];
  const rows = useMemo(() => data?.rows ?? [], [data]);

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {data ? `${data.row_count} rows · sample of ${limit}` : '—'}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCcw
              className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
        </div>
        {isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : (
          <div className="overflow-x-auto border rounded">
            <Table>
              <TableHeader>
                <TableRow>
                  {cols.map((c) => (
                    <TableHead key={c.name}>
                      <span className="font-mono text-xs">{c.name}</span>
                      <span className="ml-2 text-[10px] text-muted-foreground">
                        {c.type}
                      </span>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r, i) => (
                  <TableRow key={i}>
                    {(r as unknown[]).map((v, j) => (
                      <TableCell key={j} className="font-mono text-xs">
                        {v === null || v === undefined
                          ? '—'
                          : String(v)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
