/**
 * ChartsListPage
 * 
 * Lists all saved charts with filtering, search, and folder navigation.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Plus,
  Search,
  FolderOpen,
  BarChart3,
  LineChart,
  PieChart,
  AreaChart,
  ScatterChartIcon,
  Table2,
  Gauge,
  MoreVertical,
  Trash2,
  Copy,
  Edit,
  Eye,
  Star,
  Clock,
  ChevronRight,
  Home,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { chartService } from '@/services/chartService';
import type { Chart, ChartFolder, ChartType } from '@/components/charts/types';
import { useToast } from '@/components/ui/use-toast';

const CHART_TYPE_ICONS: Record<ChartType, React.ElementType> = {
  bar: BarChart3,
  line: LineChart,
  pie: PieChart,
  area: AreaChart,
  scatter: ScatterChartIcon,
  donut: PieChart,
  metric: Gauge,
  table: Table2,
  heatmap: BarChart3,
  gauge: Gauge,
  treemap: BarChart3,
  funnel: BarChart3,
};

const CHART_TYPE_LABELS: Record<ChartType, string> = {
  bar: 'Bar Chart',
  line: 'Line Chart',
  pie: 'Pie Chart',
  area: 'Area Chart',
  scatter: 'Scatter Plot',
  donut: 'Donut Chart',
  metric: 'Metric Card',
  table: 'Data Table',
  heatmap: 'Heatmap',
  gauge: 'Gauge',
  treemap: 'Treemap',
  funnel: 'Funnel Chart',
};

export const ChartsListPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();

  const [charts, setCharts] = useState<Chart[]>([]);
  const [folders, setFolders] = useState<ChartFolder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [chartTypeFilter, setChartTypeFilter] = useState<string>('all');
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 20,
    total: 0,
    pages: 0,
  });

  const currentFolderId = searchParams.get('folder') || undefined;

  // Load charts and folders
  useEffect(() => {
    loadCharts();
    loadFolders();
  }, [currentFolderId, pagination.page, chartTypeFilter]);

  const loadCharts = async () => {
    setIsLoading(true);
    try {
      const response = await chartService.list({
        folder_id: currentFolderId,
        page: pagination.page,
        per_page: pagination.perPage,
        chart_types: chartTypeFilter !== 'all' ? chartTypeFilter : undefined,
        search: searchQuery || undefined,
      });
      setCharts(response.items);
      setPagination({
        page: response.page,
        perPage: response.per_page,
        total: response.total,
        pages: response.pages,
      });
    } catch (error) {
      console.error('Failed to load charts:', error);
      toast({
        title: 'Error',
        description: 'Failed to load charts',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadFolders = async () => {
    try {
      const folderList = await chartService.listFolders(currentFolderId);
      setFolders(folderList);
    } catch (error) {
      console.error('Failed to load folders:', error);
    }
  };

  // Search with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      loadCharts();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleCreateChart = () => {
    navigate('/app/charts/new');
  };

  const handleEditChart = (chartId: string) => {
    navigate(`/app/charts/${chartId}/edit`);
  };

  const handleViewChart = (chartId: string) => {
    navigate(`/app/charts/${chartId}`);
  };

  const handleDuplicateChart = async (chart: Chart) => {
    try {
      await chartService.duplicate(chart.id, `${chart.name} (Copy)`);
      toast({
        title: 'Chart Duplicated',
        description: `Created a copy of "${chart.name}"`,
      });
      loadCharts();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to duplicate chart',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteChart = async (chart: Chart) => {
    if (!confirm(`Are you sure you want to delete "${chart.name}"?`)) return;

    try {
      await chartService.delete(chart.id);
      toast({
        title: 'Chart Deleted',
        description: `"${chart.name}" has been deleted`,
      });
      loadCharts();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete chart',
        variant: 'destructive',
      });
    }
  };

  const handleFolderClick = (folderId: string) => {
    setSearchParams({ folder: folderId });
  };

  const handleGoToRoot = () => {
    setSearchParams({});
  };

  // Breadcrumb navigation
  const breadcrumbs = useMemo(() => {
    // TODO: Build full breadcrumb path from current folder
    const crumbs: Array<{ id: string | null; name: string }> = [{ id: null, name: 'Charts' }];
    if (currentFolderId) {
      const currentFolder = folders.find(f => f.id === currentFolderId);
      if (currentFolder) {
        crumbs.push({ id: currentFolder.id, name: currentFolder.name });
      }
    }
    return crumbs;
  }, [currentFolderId, folders]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Charts</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Create and manage your data visualizations
          </p>
        </div>
        <Button onClick={handleCreateChart} className="gap-2">
          <Plus className="h-4 w-4" />
          New Chart
        </Button>
      </div>

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <button
          onClick={handleGoToRoot}
          className="flex items-center gap-1 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <Home className="h-4 w-4" />
          Charts
        </button>
        {currentFolderId && (
          <>
            <ChevronRight className="h-4 w-4 text-gray-400" />
            {breadcrumbs.slice(1).map((crumb) => (
              <span key={crumb.id} className="text-gray-900 dark:text-white font-medium">
                {crumb.name}
              </span>
            ))}
          </>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search charts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={chartTypeFilter} onValueChange={setChartTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Chart Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="bar">Bar Chart</SelectItem>
            <SelectItem value="line">Line Chart</SelectItem>
            <SelectItem value="pie">Pie Chart</SelectItem>
            <SelectItem value="area">Area Chart</SelectItem>
            <SelectItem value="metric">Metric Card</SelectItem>
            <SelectItem value="table">Data Table</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Folders */}
      {folders.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {folders.map((folder) => (
            <Card
              key={folder.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleFolderClick(folder.id)}
            >
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <FolderOpen className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{folder.name}</p>
                  <p className="text-xs text-gray-500">{folder.chartCount} charts</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Charts Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-32 w-full mb-4" />
                <Skeleton className="h-4 w-3/4 mb-2" />
                <Skeleton className="h-3 w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : charts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <BarChart3 className="h-16 w-16 text-gray-300 dark:text-gray-600 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No charts found
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
            {searchQuery
              ? 'Try adjusting your search or filters'
              : 'Create your first chart to start visualizing your data'}
          </p>
          <Button onClick={handleCreateChart} className="gap-2">
            <Plus className="h-4 w-4" />
            Create Chart
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {charts.map((chart) => {
            const ChartIcon = CHART_TYPE_ICONS[chart.chartType] || BarChart3;
            
            return (
              <Card
                key={chart.id}
                className="group hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleViewChart(chart.id)}
              >
                <CardContent className="p-4">
                  {/* Chart Preview */}
                  <div className="h-32 bg-gray-50 dark:bg-gray-800 rounded-lg mb-4 flex items-center justify-center">
                    <ChartIcon className="h-12 w-12 text-gray-300 dark:text-gray-600" />
                  </div>

                  {/* Chart Info */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 dark:text-white truncate">
                        {chart.name}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {CHART_TYPE_LABELS[chart.chartType]}
                      </p>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          handleViewChart(chart.id);
                        }}>
                          <Eye className="h-4 w-4 mr-2" />
                          View
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          handleEditChart(chart.id);
                        }}>
                          <Edit className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          handleDuplicateChart(chart);
                        }}>
                          <Copy className="h-4 w-4 mr-2" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-red-600"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteChart(chart);
                          }}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  {/* Tags */}
                  {chart.tags && chart.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {chart.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                      {chart.tags.length > 3 && (
                        <Badge variant="secondary" className="text-xs">
                          +{chart.tags.length - 3}
                        </Badge>
                      )}
                    </div>
                  )}

                  {/* Meta */}
                  <div className="flex items-center gap-3 mt-3 text-xs text-gray-500 dark:text-gray-400">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(chart.updatedAt || chart.createdAt)}
                    </span>
                    {chart.isPublic && (
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3" />
                        Public
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {pagination.pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={pagination.page === 1}
            onClick={() => setPagination({ ...pagination, page: pagination.page - 1 })}
          >
            Previous
          </Button>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Page {pagination.page} of {pagination.pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={pagination.page === pagination.pages}
            onClick={() => setPagination({ ...pagination, page: pagination.page + 1 })}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
  
  return date.toLocaleDateString();
}

export default ChartsListPage;
