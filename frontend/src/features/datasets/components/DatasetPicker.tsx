/**
 * DatasetPicker
 *
 * Reusable dataset selector for chart and dashboard builders. Shows the
 * dataset list (filterable by search), and exposes the selected dataset
 * upward so chart-builder UIs can populate dimension/metric pickers from
 * `dataset.columns` and `dataset.metrics` (Superset-style).
 */

import { useMemo, useState } from 'react';
import { Database, Layers, Table2, Search } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useDatasets } from '../hooks/useDatasets';
import type { Dataset } from '../types';

export interface DatasetPickerProps {
  value?: string | null;
  onChange: (datasetId: string, dataset: Dataset) => void;
  onClear?: () => void;
  placeholder?: string;
  className?: string;
  /** Restrict to managed (dbt) datasets, manual, or all. */
  filterSource?: 'all' | 'dbt' | 'manual';
}

export function DatasetPicker({
  value,
  onChange,
  onClear,
  placeholder = 'Select a dataset…',
  className,
  filterSource = 'all',
}: DatasetPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const params = useMemo(
    () => ({
      search: search || undefined,
      source: filterSource === 'all' ? undefined : filterSource,
      per_page: 50,
    }),
    [search, filterSource],
  );

  const { data, isLoading } = useDatasets(params);
  const datasets = data?.items ?? [];
  const selected = datasets.find((d) => d.id === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          className={`w-full justify-start h-auto py-2 ${className ?? ''}`}
        >
          <Database className="h-4 w-4 mr-2 shrink-0" />
          <div className="flex flex-col items-start min-w-0 flex-1">
            {selected ? (
              <>
                <span className="truncate w-full text-left">
                  {selected.name}
                </span>
                {selected.table_name && (
                  <span className="text-xs text-muted-foreground truncate w-full text-left">
                    {[selected.schema, selected.table_name]
                      .filter(Boolean)
                      .join('.')}
                  </span>
                )}
              </>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[420px] p-0" align="start">
        <div className="p-2 border-b">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              autoFocus
              className="pl-8 h-8"
              placeholder="Search datasets…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <div className="max-h-[320px] overflow-y-auto py-1">
          {isLoading ? (
            <div className="p-3 space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : datasets.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No datasets found.
            </div>
          ) : (
            datasets.map((ds) => {
              const Icon = ds.kind === 'virtual' ? Layers : Table2;
              const isSel = ds.id === value;
              return (
                <button
                  key={ds.id}
                  type="button"
                  className={`w-full flex items-start gap-2 px-3 py-2 text-left text-sm hover:bg-muted ${
                    isSel ? 'bg-muted' : ''
                  }`}
                  onClick={() => {
                    onChange(ds.id, ds);
                    setOpen(false);
                  }}
                >
                  <Icon className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate">{ds.name}</div>
                    {ds.table_name && (
                      <div className="text-xs text-muted-foreground truncate">
                        {[ds.schema, ds.table_name]
                          .filter(Boolean)
                          .join('.')}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-0.5 shrink-0">
                    <Badge variant="outline" className="text-[10px]">
                      {ds.source}
                    </Badge>
                    {ds.is_managed && (
                      <Badge className="text-[10px] bg-blue-500/15 text-blue-600">
                        dbt
                      </Badge>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
        {value && onClear && (
          <div className="border-t p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => {
                onClear();
                setOpen(false);
              }}
            >
              Clear selection
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
