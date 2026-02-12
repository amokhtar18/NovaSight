/**
 * ChartContainer Component
 * 
 * A wrapper component for charts with loading, error, and empty states.
 */

import React from 'react';
import { Loader2, AlertCircle, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ChartContainerProps {
  title?: string;
  subtitle?: string;
  isLoading?: boolean;
  error?: string | null;
  isEmpty?: boolean;
  emptyMessage?: string;
  children: React.ReactNode;
  className?: string;
  headerActions?: React.ReactNode;
  height?: number | string;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  title,
  subtitle,
  isLoading = false,
  error = null,
  isEmpty = false,
  emptyMessage = 'No data available',
  children,
  className = '',
  headerActions,
  height = 350,
}) => {
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center h-full py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading chart data...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-full py-12">
          <AlertCircle className="h-8 w-8 text-red-500 mb-2" />
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      );
    }

    if (isEmpty) {
      return (
        <div className="flex flex-col items-center justify-center h-full py-12">
          <BarChart3 className="h-8 w-8 text-gray-400 mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">{emptyMessage}</p>
        </div>
      );
    }

    return children;
  };

  return (
    <Card className={`overflow-hidden ${className}`}>
      {(title || headerActions) && (
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            {title && <CardTitle className="text-base font-medium">{title}</CardTitle>}
            {subtitle && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
            )}
          </div>
          {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
        </CardHeader>
      )}
      <CardContent className="p-4" style={{ height }}>
        {renderContent()}
      </CardContent>
    </Card>
  );
};

export default ChartContainer;
