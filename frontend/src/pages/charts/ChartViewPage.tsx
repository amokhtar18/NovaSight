/**
 * ChartViewPage
 * 
 * Full-page view of a saved chart with data display.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  Copy,
  Trash2,
  Share2,
  Download,
  RefreshCw,
  MoreVertical,
  Clock,
  Tag,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ChartRenderer, ChartContainer } from '@/components/charts';
import type { Chart, ChartData } from '@/components/charts/types';
import { chartService, ChartDataResponse } from '@/services/chartService';
import { useToast } from '@/components/ui/use-toast';

export const ChartViewPage: React.FC = () => {
  const navigate = useNavigate();
  const { chartId } = useParams();
  const { toast } = useToast();

  const [chart, setChart] = useState<Chart | null>(null);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (chartId) {
      loadChart(chartId);
    }
  }, [chartId]);

  const loadChart = async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [chartResponse, dataResponse] = await Promise.all([
        chartService.getById(id),
        chartService.getData(id),
      ]);
      setChart(chartResponse);
      setChartData(transformDataResponse(dataResponse));
    } catch (err) {
      setError('Failed to load chart');
      console.error('Error loading chart:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!chartId) return;
    setIsRefreshing(true);
    try {
      const dataResponse = await chartService.getData(chartId, true);
      setChartData(transformDataResponse(dataResponse));
      toast({
        title: 'Data Refreshed',
        description: 'Chart data has been updated',
      });
    } catch (err) {
      toast({
        title: 'Refresh Failed',
        description: 'Failed to refresh chart data',
        variant: 'destructive',
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleEdit = () => {
    navigate(`/app/charts/${chartId}/edit`);
  };

  const handleDuplicate = async () => {
    if (!chart) return;
    try {
      const newChart = await chartService.duplicate(chart.id, `${chart.name} (Copy)`);
      toast({
        title: 'Chart Duplicated',
        description: 'Opening the duplicated chart...',
      });
      navigate(`/app/charts/${newChart.id}/edit`);
    } catch (err) {
      toast({
        title: 'Duplication Failed',
        description: 'Failed to duplicate chart',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!chart) return;
    if (!confirm(`Are you sure you want to delete "${chart.name}"?`)) return;

    try {
      await chartService.delete(chart.id);
      toast({
        title: 'Chart Deleted',
        description: `"${chart.name}" has been deleted`,
      });
      navigate('/app/charts');
    } catch (err) {
      toast({
        title: 'Delete Failed',
        description: 'Failed to delete chart',
        variant: 'destructive',
      });
    }
  };

  const handleAddToDashboard = () => {
    // TODO: Open modal to select dashboard
    toast({
      title: 'Coming Soon',
      description: 'Dashboard integration will be available soon',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !chart) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <p className="text-red-500 mb-4">{error || 'Chart not found'}</p>
        <Button variant="outline" onClick={() => navigate('/app/charts')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Charts
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/app/charts')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {chart.name}
            </h1>
            {chart.description && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {chart.description}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="outline" onClick={handleAddToDashboard}>
            <ExternalLink className="h-4 w-4 mr-2" />
            Add to Dashboard
          </Button>
          <Button onClick={handleEdit}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleDuplicate}>
                <Copy className="h-4 w-4 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Share2 className="h-4 w-4 mr-2" />
                Share
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Download className="h-4 w-4 mr-2" />
                Export
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-red-600" onClick={handleDelete}>
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Chart */}
      <Card>
        <CardContent className="p-6" style={{ height: 500 }}>
          <ChartContainer
            isLoading={isRefreshing}
            isEmpty={!chartData || chartData.data.length === 0}
            height="100%"
          >
            {chartData && chartData.data.length > 0 && (
              <ChartRenderer
                type={chart.chartType}
                data={chartData}
                config={chart.vizConfig}
                dimensions={chart.queryConfig.dimensions}
                measures={chart.queryConfig.measures}
                height="100%"
              />
            )}
          </ChartContainer>
        </CardContent>
      </Card>

      {/* Metadata */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Data Info */}
        {chartData && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Data Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Rows</span>
                <span>{chartData.rowCount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Columns</span>
                <span>{chartData.columns.length}</span>
              </div>
              {chartData.executionTimeMs !== undefined && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Query Time</span>
                  <span>{chartData.executionTimeMs}ms</span>
                </div>
              )}
              {chartData.cached && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Status</span>
                  <Badge variant="secondary">Cached</Badge>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Chart Details */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Type</span>
              <span className="capitalize">{chart.chartType}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Source</span>
              <span className="capitalize">{chart.sourceType.replace('_', ' ')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Visibility</span>
              <span>{chart.isPublic ? 'Public' : 'Private'}</span>
            </div>
          </CardContent>
        </Card>

        {/* Timestamps */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">History</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center gap-2 text-gray-500">
              <Clock className="h-4 w-4" />
              <span>Created {formatDate(chart.createdAt)}</span>
            </div>
            {chart.updatedAt && (
              <div className="flex items-center gap-2 text-gray-500">
                <Clock className="h-4 w-4" />
                <span>Updated {formatDate(chart.updatedAt)}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tags */}
      {chart.tags && chart.tags.length > 0 && (
        <div className="flex items-center gap-2">
          <Tag className="h-4 w-4 text-gray-400" />
          {chart.tags.map((tag) => (
            <Badge key={tag} variant="secondary">
              {tag}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};

function transformDataResponse(response: ChartDataResponse): ChartData {
  return {
    data: response.data,
    columns: response.columns.map(c => ({
      name: c.name,
      type: c.type as 'string' | 'number' | 'datetime' | 'boolean',
    })),
    rowCount: response.row_count,
    executionTimeMs: response.execution_time_ms,
    cached: response.cached,
    cacheExpiresAt: response.cache_expires_at,
  };
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default ChartViewPage;
