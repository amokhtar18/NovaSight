/**
 * ChartBuilderPage
 * 
 * Interactive chart builder for creating and editing charts.
 * Supports dataset selection (canonical, mart-backed) and raw SQL.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Save,
  Play,
  BarChart3,
  LineChart,
  PieChart,
  AreaChart,
  ScatterChartIcon,
  Table2,
  Gauge,
  ArrowLeft,
  Database,
  Columns,
  Palette,
  ChevronDown,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChartRenderer, ChartContainer } from '@/components/charts';
import type {
  ChartType,
  ChartSourceType,
  ChartVizConfig,
  ChartQueryConfig,
  ChartData,
} from '@/components/charts/types';
import { chartService, ChartCreateRequest } from '@/services/chartService';
import { useToast } from '@/components/ui/use-toast';
import { PageHeader } from '@/components/common';
import { DatasetPicker, useDataset } from '@/features/datasets';

const CHART_TYPES: Array<{ type: ChartType; label: string; icon: React.ElementType }> = [
  { type: 'bar', label: 'Bar', icon: BarChart3 },
  { type: 'line', label: 'Line', icon: LineChart },
  { type: 'pie', label: 'Pie', icon: PieChart },
  { type: 'area', label: 'Area', icon: AreaChart },
  { type: 'scatter', label: 'Scatter', icon: ScatterChartIcon },
  { type: 'donut', label: 'Donut', icon: PieChart },
  { type: 'metric', label: 'Metric', icon: Gauge },
  { type: 'table', label: 'Table', icon: Table2 },
];

const DEFAULT_VIZ_CONFIG: ChartVizConfig = {
  showLegend: true,
  legendPosition: 'bottom',
  showDataLabels: false,
  stacked: false,
  curved: true,
  showGrid: true,
  animate: true,
};

const DEFAULT_QUERY_CONFIG: ChartQueryConfig = {
  dimensions: [],
  measures: [],
  filters: [],
  orderBy: [],
  limit: 1000,
};

export const ChartBuilderPage: React.FC = () => {
  const navigate = useNavigate();
  const { chartId } = useParams();
  const { toast } = useToast();
  const isEditing = Boolean(chartId);

  // Form state
  const [chartName, setChartName] = useState('Untitled Chart');
  const [chartDescription, setChartDescription] = useState('');
  const [chartType, setChartType] = useState<ChartType>('bar');
  const [sourceType, setSourceType] = useState<ChartSourceType>('dataset');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [sqlQuery, setSqlQuery] = useState('');
  const [queryConfig, setQueryConfig] = useState<ChartQueryConfig>(DEFAULT_QUERY_CONFIG);
  const [vizConfig, setVizConfig] = useState<ChartVizConfig>(DEFAULT_VIZ_CONFIG);
  const [tags, setTags] = useState<string[]>([]);
  const [isPublic, setIsPublic] = useState(false);

  // UI state
  const [previewData, setPreviewData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [activeTab, setActiveTab] = useState('data');

  // Load existing chart if editing
  useEffect(() => {
    if (chartId) {
      loadChart(chartId);
    }
  }, [chartId]);

  const loadChart = async (id: string) => {
    setIsLoading(true);
    try {
      const chart = await chartService.getById(id);
      setChartName(chart.name);
      setChartDescription(chart.description || '');
      setChartType(chart.chartType);
      setSourceType(chart.sourceType);
      setSelectedDatasetId(chart.datasetId || '');
      setQueryConfig(chart.queryConfig);
      setVizConfig(chart.vizConfig);
      setTags(chart.tags);
      setIsPublic(chart.isPublic);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load chart',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePreview = async () => {
    if (sourceType === 'dataset' && !selectedDatasetId) {
      toast({
        title: 'Select a Dataset',
        description: 'Please select a dataset to preview data',
        variant: 'destructive',
      });
      return;
    }

    if (sourceType === 'sql_query' && !sqlQuery.trim()) {
      toast({
        title: 'Enter SQL Query',
        description: 'Please enter a SQL query to preview data',
        variant: 'destructive',
      });
      return;
    }

    setIsPreviewing(true);
    try {
      const result = await chartService.preview({
        source_type: sourceType,
        dataset_id: sourceType === 'dataset' ? selectedDatasetId : undefined,
        sql_query: sourceType === 'sql_query' ? sqlQuery : undefined,
        query_config: queryConfig,
        limit: 100,
      });

      setPreviewData({
        data: result.data,
        columns: result.columns.map(c => ({
          name: c.name,
          type: c.type as 'string' | 'number' | 'datetime' | 'boolean',
        })),
        rowCount: result.row_count,
        executionTimeMs: result.execution_time_ms,
        cached: result.cached,
      });
    } catch (error) {
      toast({
        title: 'Preview Failed',
        description: 'Failed to preview chart data',
        variant: 'destructive',
      });
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleSave = async () => {
    if (!chartName.trim()) {
      toast({
        title: 'Enter Chart Name',
        description: 'Please enter a name for your chart',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      const chartData: ChartCreateRequest = {
        name: chartName,
        description: chartDescription,
        chart_type: chartType,
        source_type: sourceType,
        dataset_id: sourceType === 'dataset' ? selectedDatasetId : undefined,
        sql_query: sourceType === 'sql_query' ? sqlQuery : undefined,
        query_config: queryConfig,
        viz_config: vizConfig,
        tags,
        is_public: isPublic,
      };

      if (isEditing && chartId) {
        await chartService.update(chartId, chartData);
        toast({
          title: 'Chart Updated',
          description: 'Your chart has been saved',
        });
      } else {
        const newChart = await chartService.create(chartData);
        toast({
          title: 'Chart Created',
          description: 'Your chart has been saved',
        });
        navigate(`/app/charts/${newChart.id}/edit`);
      }
    } catch (error) {
      toast({
        title: 'Save Failed',
        description: 'Failed to save chart',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const toggleDimension = (dim: string) => {
    setQueryConfig(prev => ({
      ...prev,
      dimensions: prev.dimensions.includes(dim)
        ? prev.dimensions.filter(d => d !== dim)
        : [...prev.dimensions, dim],
    }));
  };

  const toggleMeasure = (measure: string) => {
    setQueryConfig(prev => ({
      ...prev,
      measures: prev.measures.includes(measure)
        ? prev.measures.filter(m => m !== measure)
        : [...prev.measures, measure],
    }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <PageHeader
          className="mb-0"
          icon={<BarChart3 className="h-5 w-5" />}
          title={isEditing ? 'Edit Chart' : 'Create Chart'}
          eyebrow={
            <button
              type="button"
              onClick={() => navigate('/app/charts')}
              className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-3 w-3" />
              Charts
            </button>
          }
          actions={
            <>
              <Button variant="outline" onClick={handlePreview} disabled={isPreviewing}>
                {isPreviewing ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                Preview
              </Button>
              <Button onClick={handleSave} disabled={isSaving}>
                {isSaving ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                Save
              </Button>
            </>
          }
        />
        <div className="mt-3 max-w-md">
          <Label htmlFor="chart-name" className="sr-only">Chart Name</Label>
          <Input
            id="chart-name"
            value={chartName}
            onChange={(e) => setChartName(e.target.value)}
            className="text-lg font-semibold"
            placeholder="Chart name..."
          />
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Configuration */}
        <div className="w-80 border-r border-gray-200 dark:border-gray-700 overflow-y-auto bg-gray-50 dark:bg-gray-900">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full rounded-none border-b">
              <TabsTrigger value="data" className="flex-1">
                <Database className="h-4 w-4 mr-2" />
                Data
              </TabsTrigger>
              <TabsTrigger value="style" className="flex-1">
                <Palette className="h-4 w-4 mr-2" />
                Style
              </TabsTrigger>
            </TabsList>

            <TabsContent value="data" className="p-4 space-y-4">
              {/* Chart Type Selection */}
              <div className="space-y-2">
                <Label>Chart Type</Label>
                <div className="grid grid-cols-4 gap-2">
                  {CHART_TYPES.map(({ type, label, icon: Icon }) => (
                    <button
                      key={type}
                      onClick={() => setChartType(type)}
                      className={`
                        flex flex-col items-center justify-center p-3 rounded-lg border transition-all
                        ${chartType === type
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-600'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                        }
                      `}
                    >
                      <Icon className="h-5 w-5 mb-1" />
                      <span className="text-xs">{label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <Separator />

              {/* Data Source */}
              <div className="space-y-2">
                <Label>Data Source</Label>
                <Select
                  value={sourceType}
                  onValueChange={(v) => setSourceType(v as ChartSourceType)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dataset">Dataset (recommended)</SelectItem>
                    <SelectItem value="sql_query">SQL Query</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {sourceType === 'dataset' ? (
                <DatasetSourcePanel
                  datasetId={selectedDatasetId}
                  onDatasetChange={(id) => setSelectedDatasetId(id)}
                  queryConfig={queryConfig}
                  onToggleDimension={toggleDimension}
                  onToggleMeasure={toggleMeasure}
                />
              ) : (
                /* SQL Query Input */
                <div className="space-y-2">
                  <Label>SQL Query</Label>
                  <Textarea
                    value={sqlQuery}
                    onChange={(e) => setSqlQuery(e.target.value)}
                    placeholder="SELECT * FROM ..."
                    className="font-mono text-sm min-h-[200px]"
                  />
                </div>
              )}

              {/* Limit */}
              <div className="space-y-2">
                <Label>Row Limit</Label>
                <Input
                  type="number"
                  value={queryConfig.limit}
                  onChange={(e) => setQueryConfig({ ...queryConfig, limit: parseInt(e.target.value) || 1000 })}
                  min={1}
                  max={10000}
                />
              </div>
            </TabsContent>

            <TabsContent value="style" className="p-4 space-y-4">
              {/* Chart Title */}
              <div className="space-y-2">
                <Label>Title</Label>
                <Input
                  value={vizConfig.title || ''}
                  onChange={(e) => setVizConfig({ ...vizConfig, title: e.target.value })}
                  placeholder="Chart title..."
                />
              </div>

              {/* Subtitle */}
              <div className="space-y-2">
                <Label>Subtitle</Label>
                <Input
                  value={vizConfig.subtitle || ''}
                  onChange={(e) => setVizConfig({ ...vizConfig, subtitle: e.target.value })}
                  placeholder="Chart subtitle..."
                />
              </div>

              <Separator />

              {/* Legend */}
              <div className="flex items-center justify-between">
                <Label>Show Legend</Label>
                <Switch
                  checked={vizConfig.showLegend !== false}
                  onCheckedChange={(checked) => setVizConfig({ ...vizConfig, showLegend: checked })}
                />
              </div>

              {vizConfig.showLegend !== false && (
                <div className="space-y-2">
                  <Label>Legend Position</Label>
                  <Select
                    value={vizConfig.legendPosition || 'bottom'}
                    onValueChange={(v) => setVizConfig({ ...vizConfig, legendPosition: v as 'top' | 'bottom' })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="top">Top</SelectItem>
                      <SelectItem value="bottom">Bottom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              <Separator />

              {/* Grid */}
              <div className="flex items-center justify-between">
                <Label>Show Grid</Label>
                <Switch
                  checked={vizConfig.showGrid !== false}
                  onCheckedChange={(checked) => setVizConfig({ ...vizConfig, showGrid: checked })}
                />
              </div>

              {/* Data Labels */}
              <div className="flex items-center justify-between">
                <Label>Show Data Labels</Label>
                <Switch
                  checked={vizConfig.showDataLabels === true}
                  onCheckedChange={(checked) => setVizConfig({ ...vizConfig, showDataLabels: checked })}
                />
              </div>

              {/* Stacked (for bar/area) */}
              {(chartType === 'bar' || chartType === 'area') && (
                <div className="flex items-center justify-between">
                  <Label>Stacked</Label>
                  <Switch
                    checked={vizConfig.stacked === true}
                    onCheckedChange={(checked) => setVizConfig({ ...vizConfig, stacked: checked })}
                  />
                </div>
              )}

              {/* Curved (for line/area) */}
              {(chartType === 'line' || chartType === 'area') && (
                <div className="flex items-center justify-between">
                  <Label>Curved Lines</Label>
                  <Switch
                    checked={vizConfig.curved !== false}
                    onCheckedChange={(checked) => setVizConfig({ ...vizConfig, curved: checked })}
                  />
                </div>
              )}

              <Separator />

              {/* Description */}
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={chartDescription}
                  onChange={(e) => setChartDescription(e.target.value)}
                  placeholder="Describe this chart..."
                  rows={3}
                />
              </div>

              {/* Public */}
              <div className="flex items-center justify-between">
                <div>
                  <Label>Public</Label>
                  <p className="text-xs text-gray-500">Allow others in your tenant to view</p>
                </div>
                <Switch
                  checked={isPublic}
                  onCheckedChange={setIsPublic}
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Panel - Preview */}
        <div className="flex-1 overflow-auto p-6 bg-white dark:bg-gray-950">
          <ChartContainer
            title={vizConfig.title || chartName}
            subtitle={vizConfig.subtitle}
            isLoading={isPreviewing}
            isEmpty={!previewData || previewData.data.length === 0}
            emptyMessage="Configure your chart and click Preview to see results"
            height={400}
          >
            {previewData && previewData.data.length > 0 && (
              <ChartRenderer
                type={chartType}
                data={previewData}
                config={vizConfig}
                dimensions={queryConfig.dimensions}
                measures={queryConfig.measures}
                height="100%"
              />
            )}
          </ChartContainer>

          {/* Data Info */}
          {previewData && (
            <div className="mt-4 text-sm text-gray-500 dark:text-gray-400 flex items-center gap-4">
              <span>{previewData.rowCount} rows</span>
              <span>{previewData.columns.length} columns</span>
              {previewData.executionTimeMs !== undefined && (
                <span>{previewData.executionTimeMs}ms</span>
              )}
              {previewData.cached && (
                <Badge variant="secondary">Cached</Badge>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// Dataset source panel — Superset-style explore left rail when sourcing from
// a Dataset. Renders dimensions from `dataset.columns` (groupby=true) and
// metrics from `dataset.metrics`. Falls back to all visible columns as
// pseudo-measures when no metrics are defined.
// =============================================================================

interface DatasetSourcePanelProps {
  datasetId: string;
  onDatasetChange: (id: string) => void;
  queryConfig: ChartQueryConfig;
  onToggleDimension: (name: string) => void;
  onToggleMeasure: (name: string) => void;
}

const DatasetSourcePanel: React.FC<DatasetSourcePanelProps> = ({
  datasetId,
  onDatasetChange,
  queryConfig,
  onToggleDimension,
  onToggleMeasure,
}) => {
  const { data: dataset } = useDataset(datasetId || undefined);

  const dimensionCols = (dataset?.columns ?? []).filter(
    (c) => c.groupby && !c.is_hidden,
  );
  const metricList = dataset?.metrics ?? [];

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <Label>Dataset</Label>
        <DatasetPicker
          value={datasetId || null}
          onChange={(id) => onDatasetChange(id)}
          onClear={() => onDatasetChange('')}
        />
      </div>

      {dataset && (
        <>
          <Collapsible defaultOpen>
            <CollapsibleTrigger className="flex items-center justify-between w-full py-2">
              <Label className="flex items-center gap-2">
                <Columns className="h-4 w-4" />
                Dimensions ({dimensionCols.length})
              </Label>
              <ChevronDown className="h-4 w-4" />
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1">
              {dimensionCols.length === 0 && (
                <p className="text-xs text-muted-foreground p-2">
                  No groupable columns.
                </p>
              )}
              {dimensionCols.map((c) => {
                const sel = queryConfig.dimensions.includes(c.column_name);
                return (
                  <div
                    key={c.column_name}
                    onClick={() => onToggleDimension(c.column_name)}
                    className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                      sel
                        ? 'bg-blue-100 dark:bg-blue-900/30'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded border flex items-center justify-center ${
                        sel
                          ? 'bg-blue-500 border-blue-500 text-white'
                          : 'border-gray-300'
                      }`}
                    >
                      {sel && '✓'}
                    </div>
                    <span className="text-sm flex-1 truncate">
                      {c.verbose_name || c.column_name}
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {c.type}
                    </span>
                  </div>
                );
              })}
            </CollapsibleContent>
          </Collapsible>

          <Collapsible defaultOpen>
            <CollapsibleTrigger className="flex items-center justify-between w-full py-2">
              <Label className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Metrics ({metricList.length})
              </Label>
              <ChevronDown className="h-4 w-4" />
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1">
              {metricList.length === 0 && (
                <p className="text-xs text-muted-foreground p-2">
                  No metrics defined.{' '}
                  <a
                    href={`/app/datasets/${dataset.id}`}
                    className="underline"
                  >
                    Define metrics
                  </a>{' '}
                  on the dataset to reuse them across charts.
                </p>
              )}
              {metricList.map((m) => {
                const sel = queryConfig.measures.includes(m.metric_name);
                return (
                  <div
                    key={m.metric_name}
                    onClick={() => onToggleMeasure(m.metric_name)}
                    className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                      sel
                        ? 'bg-green-100 dark:bg-green-900/30'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded border flex items-center justify-center ${
                        sel
                          ? 'bg-green-500 border-green-500 text-white'
                          : 'border-gray-300'
                      }`}
                    >
                      {sel && '✓'}
                    </div>
                    <span className="text-sm flex-1 truncate">
                      {m.verbose_name || m.metric_name}
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[100px]">
                      {m.expression}
                    </span>
                  </div>
                );
              })}
            </CollapsibleContent>
          </Collapsible>
        </>
      )}
    </div>
  );
};

export default ChartBuilderPage;
