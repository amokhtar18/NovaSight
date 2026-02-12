/**
 * Add Chart to Dashboard Dialog
 * 
 * Allows users to select from saved charts and add them to the dashboard.
 */

import { useState, useMemo } from 'react';
import {
  BarChart3,
  Plus,
  Search,
  FolderOpen,
  Clock,
  LayoutGrid,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/use-toast';
import { chartService } from '@/services/chartService';
import type { Chart, ChartFolder } from '@/components/charts/types';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';

interface AddChartToDashboardDialogProps {
  dashboardId: string;
  existingChartIds?: string[];
}

const CHART_TYPE_ICONS: Record<string, string> = {
  bar: '📊',
  line: '📈',
  pie: '🥧',
  area: '📉',
  scatter: '⚬',
  donut: '🍩',
  metric: '🔢',
  table: '📋',
};

export function AddChartToDashboardDialog({
  dashboardId,
  existingChartIds = [],
}: AddChartToDashboardDialogProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [selectedChartIds, setSelectedChartIds] = useState<string[]>([]);
  
  // Fetch charts
  const { data: chartsData, isLoading: chartsLoading } = useQuery({
    queryKey: ['charts', 'all', searchQuery, selectedFolderId],
    queryFn: async () => {
      const params: {
        page?: number;
        page_size?: number;
        search?: string;
        folder_id?: string;
      } = {
        page: 1,
        page_size: 100,
      };
      if (searchQuery) params.search = searchQuery;
      if (selectedFolderId) params.folder_id = selectedFolderId;
      return chartService.list(params);
    },
    enabled: open,
  });
  
  // Fetch folders
  const { data: foldersData } = useQuery({
    queryKey: ['chart-folders'],
    queryFn: () => chartService.listFolders(),
    enabled: open,
  });
  
  // Add charts mutation
  const addChartsMutation = useMutation({
    mutationFn: async (chartIds: string[]) => {
      // Add each chart to the dashboard
      const promises = chartIds.map((chartId, index) =>
        chartService.addToDashboard(dashboardId, chartId, {
          grid_position: {
            x: (index % 2) * 6,
            y: Math.floor(index / 2) * 4,
            w: 6,
            h: 4,
          },
        })
      );
      return Promise.all(promises);
    },
    onSuccess: () => {
      toast({
        title: 'Charts Added',
        description: `Added ${selectedChartIds.length} chart(s) to the dashboard`,
      });
      queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] });
      setOpen(false);
      setSelectedChartIds([]);
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to add charts to dashboard',
        variant: 'destructive',
      });
    },
  });
  
  // Filter out already-added charts
  const availableCharts = useMemo(() => {
    const charts = chartsData?.items || [];
    return charts.filter(chart => !existingChartIds.includes(chart.id));
  }, [chartsData?.items, existingChartIds]);
  
  // Recent charts (created in last 7 days)
  const recentCharts = useMemo(() => {
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    return availableCharts.filter(
      chart => new Date(chart.createdAt) > sevenDaysAgo
    );
  }, [availableCharts]);
  
  const toggleChartSelection = (chartId: string) => {
    setSelectedChartIds(prev =>
      prev.includes(chartId)
        ? prev.filter(id => id !== chartId)
        : [...prev, chartId]
    );
  };
  
  const handleAddCharts = () => {
    if (selectedChartIds.length === 0) return;
    addChartsMutation.mutate(selectedChartIds);
  };
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          className="fixed bottom-20 right-6 rounded-full shadow-lg"
          size="lg"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Chart
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-3xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LayoutGrid className="h-5 w-5" />
            Add Charts to Dashboard
          </DialogTitle>
          <DialogDescription>
            Select saved charts to add to your dashboard
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search charts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          {/* Tabs */}
          <Tabs defaultValue="all">
            <TabsList>
              <TabsTrigger value="all" className="flex items-center gap-1">
                <BarChart3 className="h-4 w-4" />
                All Charts
              </TabsTrigger>
              <TabsTrigger value="recent" className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                Recent
              </TabsTrigger>
              <TabsTrigger value="folders" className="flex items-center gap-1">
                <FolderOpen className="h-4 w-4" />
                By Folder
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="all" className="mt-4">
              <ChartList
                charts={availableCharts}
                isLoading={chartsLoading}
                selectedIds={selectedChartIds}
                onToggle={toggleChartSelection}
              />
            </TabsContent>
            
            <TabsContent value="recent" className="mt-4">
              <ChartList
                charts={recentCharts}
                isLoading={chartsLoading}
                selectedIds={selectedChartIds}
                onToggle={toggleChartSelection}
                emptyMessage="No charts created in the last 7 days"
              />
            </TabsContent>
            
            <TabsContent value="folders" className="mt-4">
              <div className="flex gap-4">
                {/* Folder List */}
                <div className="w-48 border-r pr-4">
                  <ScrollArea className="h-64">
                    <div className="space-y-1">
                      <button
                        onClick={() => setSelectedFolderId(null)}
                        className={`
                          w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md
                          ${!selectedFolderId ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}
                        `}
                      >
                        <FolderOpen className="h-4 w-4" />
                        All Folders
                      </button>
                      {foldersData?.map((folder: ChartFolder) => (
                        <button
                          key={folder.id}
                          onClick={() => setSelectedFolderId(folder.id)}
                          className={`
                            w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md
                            ${selectedFolderId === folder.id ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}
                          `}
                        >
                          <FolderOpen className="h-4 w-4" />
                          {folder.name}
                        </button>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
                
                {/* Charts in selected folder */}
                <div className="flex-1">
                  <ChartList
                    charts={availableCharts}
                    isLoading={chartsLoading}
                    selectedIds={selectedChartIds}
                    onToggle={toggleChartSelection}
                  />
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
        
        {/* Footer with selection count and add button */}
        <div className="flex items-center justify-between pt-4 border-t mt-4">
          <div className="text-sm text-muted-foreground">
            {selectedChartIds.length > 0
              ? `${selectedChartIds.length} chart(s) selected`
              : 'Select charts to add'}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddCharts}
              disabled={selectedChartIds.length === 0 || addChartsMutation.isPending}
            >
              {addChartsMutation.isPending
                ? 'Adding...'
                : `Add ${selectedChartIds.length || ''} Chart${selectedChartIds.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface ChartListProps {
  charts: Chart[];
  isLoading: boolean;
  selectedIds: string[];
  onToggle: (id: string) => void;
  emptyMessage?: string;
}

function ChartList({
  charts,
  isLoading,
  selectedIds,
  onToggle,
  emptyMessage = 'No charts available',
}: ChartListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }
  
  if (charts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <BarChart3 className="h-8 w-8 mb-2" />
        <p>{emptyMessage}</p>
      </div>
    );
  }
  
  return (
    <ScrollArea className="h-64">
      <div className="space-y-2">
        {charts.map((chart) => (
          <button
            key={chart.id}
            onClick={() => onToggle(chart.id)}
            className={`
              w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-all
              ${selectedIds.includes(chart.id)
                ? 'border-primary bg-primary/5 ring-1 ring-primary'
                : 'hover:bg-muted/50'}
            `}
          >
            {/* Selection indicator */}
            <div
              className={`
                w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs
                ${selectedIds.includes(chart.id)
                  ? 'bg-primary border-primary text-white'
                  : 'border-gray-300'}
              `}
            >
              {selectedIds.includes(chart.id) && '✓'}
            </div>
            
            {/* Chart icon */}
            <span className="text-xl">
              {CHART_TYPE_ICONS[chart.chartType] || '📊'}
            </span>
            
            {/* Chart info */}
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">{chart.name}</div>
              <div className="text-xs text-muted-foreground flex items-center gap-2">
                <Badge variant="outline" className="text-xs capitalize">
                  {chart.chartType}
                </Badge>
                <span>
                  Updated {formatDistanceToNow(new Date(chart.updatedAt || chart.createdAt), { addSuffix: true })}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </ScrollArea>
  );
}

export default AddChartToDashboardDialog;
