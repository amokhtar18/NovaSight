/**
 * DatasetsListPage
 *
 * Superset-inspired datasets browser. Lists all datasets available to the
 * current tenant, supports filtering, full-text search, and triggers a
 * one-click sync from materialized dbt models.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database,
  Plus,
  RefreshCcw,
  Search,
  Trash2,
  Star,
  Eye,
  Layers,
  Table2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PageHeader } from '@/components/common';
import { useToast } from '@/components/ui/use-toast';
import {
  useDatasets,
  useDeleteDataset,
  useSyncDatasetsFromDbt,
} from '../hooks/useDatasets';
import type {
  Dataset,
  DatasetKind,
  DatasetSource,
} from '../types';

const KIND_LABELS: Record<DatasetKind, string> = {
  physical: 'Physical',
  virtual: 'Virtual',
};

const SOURCE_LABELS: Record<DatasetSource, string> = {
  dbt: 'dbt',
  manual: 'Manual',
  sql_lab: 'SQL Lab',
};

export default function DatasetsListPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [kind, setKind] = useState<'all' | DatasetKind>('all');
  const [source, setSource] = useState<'all' | DatasetSource>('all');

  const params = useMemo(
    () => ({
      search: search || undefined,
      kind: kind === 'all' ? undefined : kind,
      source: source === 'all' ? undefined : source,
      per_page: 100,
    }),
    [search, kind, source],
  );

  const { data, isLoading, isFetching, refetch } = useDatasets(params);
  const syncDbt = useSyncDatasetsFromDbt();
  const remove = useDeleteDataset();

  const datasets = data?.items ?? [];

  const handleSync = async () => {
    try {
      const res = await syncDbt.mutateAsync(true);
      toast({
        title: 'Datasets synced from dbt',
        description: `Created ${res.created}, updated ${res.updated}, deactivated ${res.deactivated}.`,
      });
      if (res.errors?.length) {
        toast({
          title: 'Some models were skipped',
          description: res.errors.slice(0, 3).join('\n'),
          variant: 'destructive',
        });
      }
    } catch (err) {
      toast({
        title: 'Sync failed',
        description: err instanceof Error ? err.message : String(err),
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (ds: Dataset) => {
    if (!window.confirm(`Delete dataset "${ds.name}"?`)) return;
    try {
      await remove.mutateAsync({ id: ds.id });
      toast({ title: 'Dataset deleted', description: ds.name });
    } catch (err) {
      toast({
        title: 'Delete failed',
        description: err instanceof Error ? err.message : String(err),
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <PageHeader
        title="Datasets"
        description="Reusable, governed data sources for charts and dashboards (Superset-inspired). Sync materialized dbt models with one click."
        icon={<Database className="h-6 w-6" />}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleSync}
              disabled={syncDbt.isPending}
            >
              <RefreshCcw
                className={`h-4 w-4 mr-2 ${
                  syncDbt.isPending ? 'animate-spin' : ''
                }`}
              />
              Sync from dbt
            </Button>
            <Button onClick={() => navigate('/app/datasets/new')}>
              <Plus className="h-4 w-4 mr-2" />
              New dataset
            </Button>
          </div>
        }
      />

      <Card>
        <CardContent className="p-4 flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search datasets…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <Select value={kind} onValueChange={(v) => setKind(v as 'all' | DatasetKind)}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Kind" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All kinds</SelectItem>
              <SelectItem value="physical">Physical</SelectItem>
              <SelectItem value="virtual">Virtual</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={source}
            onValueChange={(v) => setSource(v as 'all' | DatasetSource)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sources</SelectItem>
              <SelectItem value="dbt">dbt</SelectItem>
              <SelectItem value="manual">Manual</SelectItem>
              <SelectItem value="sql_lab">SQL Lab</SelectItem>
            </SelectContent>
          </Select>

          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            <RefreshCcw
              className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
            />
          </Button>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : datasets.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Database className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">
              No datasets yet. Sync your materialized dbt models to get started.
            </p>
            <Button onClick={handleSync} disabled={syncDbt.isPending}>
              <RefreshCcw className="h-4 w-4 mr-2" />
              Sync from dbt
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {datasets.map((ds) => (
            <DatasetCard
              key={ds.id}
              dataset={ds}
              onOpen={() => navigate(`/datasets/${ds.id}`)}
              onDelete={() => handleDelete(ds)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface DatasetCardProps {
  dataset: Dataset;
  onOpen: () => void;
  onDelete: () => void;
}

function DatasetCard({ dataset, onOpen, onDelete }: DatasetCardProps) {
  const Icon = dataset.kind === 'virtual' ? Layers : Table2;
  return (
    <Card
      className="hover:border-primary/40 transition-colors cursor-pointer"
      onClick={onOpen}
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <Icon className="h-5 w-5 text-primary shrink-0" />
            <div className="min-w-0">
              <div className="font-medium truncate flex items-center gap-1">
                {dataset.name}
                {dataset.is_featured && (
                  <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                )}
              </div>
              {dataset.table_name && (
                <div className="text-xs text-muted-foreground truncate">
                  {[dataset.schema, dataset.table_name]
                    .filter(Boolean)
                    .join('.')}
                </div>
              )}
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger
              asChild
              onClick={(e) => e.stopPropagation()}
            >
              <Button size="icon" variant="ghost" className="h-8 w-8">
                <Eye className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onOpen}>
                <Eye className="h-4 w-4 mr-2" />
                View / Edit
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <Badge variant="secondary">{KIND_LABELS[dataset.kind]}</Badge>
          <Badge variant="outline">{SOURCE_LABELS[dataset.source]}</Badge>
          {dataset.dbt_materialization && (
            <Badge variant="outline">{dataset.dbt_materialization}</Badge>
          )}
          {dataset.is_managed && (
            <Badge className="bg-blue-500/15 text-blue-600 hover:bg-blue-500/25">
              Managed
            </Badge>
          )}
        </div>

        {dataset.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {dataset.description}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
