/**
 * SQLResultsChart Component
 * 
 * Quick chart visualization for SQL Editor results.
 * Limited to bar, line, and pie charts.
 */

import React, { useState, useMemo } from 'react';
import {
  BarChart3,
  LineChart,
  PieChart,
  Table2,
  Settings,
  Save,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ChartRenderer } from '@/components/charts';
import type { ChartData, ChartVizConfig } from '@/components/charts/types';
import type { SqlQueryResult } from '../types';
import { ResultsTable } from './ResultsTable';
import { chartService } from '@/services/chartService';
import { useToast } from '@/components/ui/use-toast';

type SQLChartType = 'bar' | 'line' | 'pie';

interface SQLResultsChartProps {
  result: SqlQueryResult;
  sqlQuery: string;
  className?: string;
}

export const SQLResultsChart: React.FC<SQLResultsChartProps> = ({
  result,
  sqlQuery,
  className = '',
}) => {
  const { toast } = useToast();
  
  // View mode
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table');
  const [chartType, setChartType] = useState<SQLChartType>('bar');
  
  // Chart configuration
  const [xColumn, setXColumn] = useState<string>('');
  const [yColumns, setYColumns] = useState<string[]>([]);
  
  // Save dialog
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [chartName, setChartName] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  
  // Derive columns from result
  const columns = useMemo(() => {
    if (!result.rows || result.rows.length === 0) return [];
    return Object.keys(result.rows[0]);
  }, [result.rows]);
  
  // Categorize columns by type
  const { stringColumns, numberColumns } = useMemo(() => {
    if (!result.rows || result.rows.length === 0) {
      return { stringColumns: [], numberColumns: [] };
    }
    
    const sample = result.rows[0];
    const strings: string[] = [];
    const numbers: string[] = [];
    
    Object.entries(sample).forEach(([key, value]) => {
      if (typeof value === 'number' || (typeof value === 'string' && !isNaN(Number(value)))) {
        numbers.push(key);
      } else {
        strings.push(key);
      }
    });
    
    return { stringColumns: strings, numberColumns: numbers };
  }, [result.rows]);
  
  // Auto-select columns when switching to chart view
  React.useEffect(() => {
    if (viewMode === 'chart' && !xColumn && stringColumns.length > 0) {
      setXColumn(stringColumns[0]);
    }
    if (viewMode === 'chart' && yColumns.length === 0 && numberColumns.length > 0) {
      setYColumns([numberColumns[0]]);
    }
  }, [viewMode, stringColumns, numberColumns, xColumn, yColumns.length]);
  
  // Prepare chart data
  const chartData: ChartData = useMemo(() => {
    const data = result.rows.map(row => {
      const item: Record<string, unknown> = {};
      if (xColumn) item[xColumn] = row[xColumn];
      yColumns.forEach(col => {
        item[col] = Number(row[col]) || 0;
      });
      return item;
    });
    
    const cols = [
      ...(xColumn ? [{ name: xColumn, type: 'string' as const }] : []),
      ...yColumns.map(col => ({ name: col, type: 'number' as const })),
    ];
    
    return {
      data,
      columns: cols,
      rowCount: data.length,
    };
  }, [result.rows, xColumn, yColumns]);
  
  const vizConfig: ChartVizConfig = {
    showLegend: true,
    legendPosition: 'bottom',
    showGrid: true,
    animate: true,
  };
  
  const toggleYColumn = (col: string) => {
    setYColumns(prev =>
      prev.includes(col)
        ? prev.filter(c => c !== col)
        : [...prev, col]
    );
  };
  
  const handleSaveAsChart = async () => {
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
      await chartService.saveFromSQLEditor({
        name: chartName,
        chart_type: chartType,
        sql_query: sqlQuery,
        x_column: xColumn,
        y_columns: yColumns,
      });
      
      toast({
        title: 'Chart Saved',
        description: `"${chartName}" has been saved to your charts`,
      });
      setSaveDialogOpen(false);
      setChartName('');
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
  
  const canShowChart = columns.length > 0 && numberColumns.length > 0;
  
  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/50">
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center rounded-lg border bg-background p-0.5">
            <Button
              variant={viewMode === 'table' ? 'secondary' : 'ghost'}
              size="sm"
              className="h-7 px-3"
              onClick={() => setViewMode('table')}
            >
              <Table2 className="h-4 w-4 mr-1" />
              Table
            </Button>
            <Button
              variant={viewMode === 'chart' ? 'secondary' : 'ghost'}
              size="sm"
              className="h-7 px-3"
              onClick={() => setViewMode('chart')}
              disabled={!canShowChart}
              title={!canShowChart ? 'No numeric columns available for charting' : undefined}
            >
              <BarChart3 className="h-4 w-4 mr-1" />
              Chart
            </Button>
          </div>
          
          {/* Chart Type Selector (when in chart mode) */}
          {viewMode === 'chart' && (
            <div className="flex items-center gap-1 ml-2">
              <Button
                variant={chartType === 'bar' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-8 w-8"
                onClick={() => setChartType('bar')}
                title="Bar Chart"
              >
                <BarChart3 className="h-4 w-4" />
              </Button>
              <Button
                variant={chartType === 'line' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-8 w-8"
                onClick={() => setChartType('line')}
                title="Line Chart"
              >
                <LineChart className="h-4 w-4" />
              </Button>
              <Button
                variant={chartType === 'pie' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-8 w-8"
                onClick={() => setChartType('pie')}
                title="Pie Chart"
              >
                <PieChart className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
        
        {/* Actions */}
        {viewMode === 'chart' && (
          <div className="flex items-center gap-2">
            {/* Column Configuration */}
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm" className="h-8">
                  <Settings className="h-4 w-4 mr-1" />
                  Configure
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-64" align="end">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>X-Axis (Category)</Label>
                    <Select value={xColumn} onValueChange={setXColumn}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select column..." />
                      </SelectTrigger>
                      <SelectContent>
                        {columns.map(col => (
                          <SelectItem key={col} value={col}>{col}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Y-Axis (Values)</Label>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {numberColumns.map(col => (
                        <button
                          key={col}
                          onClick={() => toggleYColumn(col)}
                          className={`
                            flex items-center gap-2 w-full px-2 py-1.5 text-sm rounded
                            ${yColumns.includes(col)
                              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                              : 'hover:bg-muted'
                            }
                          `}
                        >
                          <div className={`
                            w-4 h-4 rounded border flex items-center justify-center text-xs
                            ${yColumns.includes(col) ? 'bg-blue-500 border-blue-500 text-white' : 'border-gray-300'}
                          `}>
                            {yColumns.includes(col) && '✓'}
                          </div>
                          {col}
                        </button>
                      ))}
                      {numberColumns.length === 0 && (
                        <p className="text-xs text-muted-foreground px-2 py-1">
                          No numeric columns available
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
            
            {/* Save as Chart */}
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => setSaveDialogOpen(true)}
              disabled={!xColumn || yColumns.length === 0}
            >
              <Save className="h-4 w-4 mr-1" />
              Save as Chart
            </Button>
          </div>
        )}
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'chart' ? (
          <div className="p-4 h-full">
            {xColumn && yColumns.length > 0 ? (
              <ChartRenderer
                type={chartType}
                data={chartData}
                config={vizConfig}
                dimensions={[xColumn]}
                measures={yColumns}
                height="100%"
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <Settings className="h-8 w-8 mb-2" />
                <p>Configure chart columns to visualize data</p>
                <p className="text-xs mt-1">Click "Configure" to select X and Y axis columns</p>
              </div>
            )}
          </div>
        ) : (
          <ResultsTable result={result} className="h-full" />
        )}
      </div>
      
      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save as Chart</DialogTitle>
            <DialogDescription>
              Save this visualization as a reusable chart
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="chartName">Chart Name</Label>
              <Input
                id="chartName"
                value={chartName}
                onChange={(e) => setChartName(e.target.value)}
                placeholder="e.g., Monthly Sales by Region"
              />
            </div>
            <div className="text-sm text-muted-foreground">
              <p>Chart Type: <span className="capitalize font-medium">{chartType}</span></p>
              <p>X-Axis: <span className="font-medium">{xColumn}</span></p>
              <p>Y-Axis: <span className="font-medium">{yColumns.join(', ')}</span></p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveAsChart} disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Chart'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SQLResultsChart;
