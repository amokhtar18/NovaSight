/**
 * ChartBuilderPage
 * 
 * Interactive chart builder for creating and editing charts.
 * Supports semantic model selection and query configuration.
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

interface SemanticModel {
  id: string;
  name: string;
  description?: string;
  dimensions: string[];
  measures: string[];
}

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
  const [sourceType, setSourceType] = useState<ChartSourceType>('semantic_model');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [sqlQuery, setSqlQuery] = useState('');
  const [queryConfig, setQueryConfig] = useState<ChartQueryConfig>(DEFAULT_QUERY_CONFIG);
  const [vizConfig, setVizConfig] = useState<ChartVizConfig>(DEFAULT_VIZ_CONFIG);
  const [tags, setTags] = useState<string[]>([]);
  const [isPublic, setIsPublic] = useState(false);

  // UI state
  const [semanticModels, setSemanticModels] = useState<SemanticModel[]>([]);
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

  // Load semantic models
  useEffect(() => {
    loadSemanticModels();
  }, []);

  const loadChart = async (id: string) => {
    setIsLoading(true);
    try {
      const chart = await chartService.getById(id);
      setChartName(chart.name);
      setChartDescription(chart.description || '');
      setChartType(chart.chartType);
      setSourceType(chart.sourceType);
      setSelectedModel(chart.semanticModelId || '');
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

  const loadSemanticModels = async () => {
    // TODO: Fetch actual semantic models from API
    // For now, use mock data
    setSemanticModels([
      {
        id: '1',
        name: 'Sales Analytics',
        description: 'Sales and revenue metrics',
        dimensions: ['date', 'product_category', 'region', 'customer_segment'],
        measures: ['total_revenue', 'order_count', 'avg_order_value', 'units_sold'],
      },
      {
        id: '2',
        name: 'Customer Analytics',
        description: 'Customer behavior and segmentation',
        dimensions: ['customer_id', 'signup_date', 'segment', 'country'],
        measures: ['lifetime_value', 'total_orders', 'churn_score'],
      },
    ]);
  };

  const handlePreview = async () => {
    if (sourceType === 'semantic_model' && !selectedModel) {
      toast({
        title: 'Select a Semantic Model',
        description: 'Please select a semantic model to preview data',
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
        semantic_model_id: sourceType === 'semantic_model' ? selectedModel : undefined,
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
        semantic_model_id: sourceType === 'semantic_model' ? selectedModel : undefined,
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

  const selectedModelData = semanticModels.find(m => m.id === selectedModel);

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
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/app/charts')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <Input
              value={chartName}
              onChange={(e) => setChartName(e.target.value)}
              className="text-lg font-semibold border-none px-0 focus-visible:ring-0 bg-transparent"
              placeholder="Chart name..."
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
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
                    <SelectItem value="semantic_model">Semantic Model</SelectItem>
                    <SelectItem value="sql_query">SQL Query</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {sourceType === 'semantic_model' ? (
                <>
                  {/* Semantic Model Selection */}
                  <div className="space-y-2">
                    <Label>Semantic Model</Label>
                    <Select value={selectedModel} onValueChange={setSelectedModel}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a model..." />
                      </SelectTrigger>
                      <SelectContent>
                        {semanticModels.map((model) => (
                          <SelectItem key={model.id} value={model.id}>
                            {model.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {selectedModelData && (
                    <>
                      {/* Dimensions */}
                      <Collapsible defaultOpen>
                        <CollapsibleTrigger className="flex items-center justify-between w-full py-2">
                          <Label className="flex items-center gap-2">
                            <Columns className="h-4 w-4" />
                            Dimensions
                          </Label>
                          <ChevronDown className="h-4 w-4" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-2">
                          {selectedModelData.dimensions.map((dim) => (
                            <div
                              key={dim}
                              onClick={() => toggleDimension(dim)}
                              className={`
                                flex items-center gap-2 p-2 rounded cursor-pointer transition-colors
                                ${queryConfig.dimensions.includes(dim)
                                  ? 'bg-blue-100 dark:bg-blue-900/30'
                                  : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                                }
                              `}
                            >
                              <div className={`
                                w-4 h-4 rounded border flex items-center justify-center
                                ${queryConfig.dimensions.includes(dim)
                                  ? 'bg-blue-500 border-blue-500 text-white'
                                  : 'border-gray-300'
                                }
                              `}>
                                {queryConfig.dimensions.includes(dim) && '✓'}
                              </div>
                              <span className="text-sm">{dim}</span>
                            </div>
                          ))}
                        </CollapsibleContent>
                      </Collapsible>

                      {/* Measures */}
                      <Collapsible defaultOpen>
                        <CollapsibleTrigger className="flex items-center justify-between w-full py-2">
                          <Label className="flex items-center gap-2">
                            <BarChart3 className="h-4 w-4" />
                            Measures
                          </Label>
                          <ChevronDown className="h-4 w-4" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-2">
                          {selectedModelData.measures.map((measure) => (
                            <div
                              key={measure}
                              onClick={() => toggleMeasure(measure)}
                              className={`
                                flex items-center gap-2 p-2 rounded cursor-pointer transition-colors
                                ${queryConfig.measures.includes(measure)
                                  ? 'bg-green-100 dark:bg-green-900/30'
                                  : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                                }
                              `}
                            >
                              <div className={`
                                w-4 h-4 rounded border flex items-center justify-center
                                ${queryConfig.measures.includes(measure)
                                  ? 'bg-green-500 border-green-500 text-white'
                                  : 'border-gray-300'
                                }
                              `}>
                                {queryConfig.measures.includes(measure) && '✓'}
                              </div>
                              <span className="text-sm">{measure}</span>
                            </div>
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    </>
                  )}
                </>
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

export default ChartBuilderPage;
