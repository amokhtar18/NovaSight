/**
 * DatasetCreatePage
 * =================
 *
 * Restricted dataset creation wizard. Datasets can only be created from
 * the tenant's curated dbt **mart** database (``tenant_<slug>_marts``) —
 * raw / staging / intermediate layers are intentionally hidden so
 * analysts cannot publish charts on top of un-modelled data.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Database,
  Lock,
  Search,
  Table2,
  Loader2,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/common';
import { useToast } from '@/components/ui/use-toast';

import { datasetsApi } from '../services/datasetsApi';
import { useCreateDataset } from '../hooks/useDatasets';
import type { MartTable, MartTablesResponse } from '../types';

const MART_TABLES_QK = ['datasets', 'mart-tables'] as const;

export default function DatasetCreatePage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const createDataset = useCreateDataset();

  const martQuery = useQuery<MartTablesResponse>({
    queryKey: MART_TABLES_QK,
    queryFn: () => datasetsApi.listMartTables(),
  });

  const [search, setSearch] = useState('');
  const [selectedTable, setSelectedTable] = useState<MartTable | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const martDb = martQuery.data?.database ?? '';
  const martExists = martQuery.data?.exists ?? false;
  const tables = martQuery.data?.tables ?? [];

  const filteredTables = useMemo(() => {
    if (!search.trim()) return tables;
    const q = search.toLowerCase();
    return tables.filter((t) => t.name.toLowerCase().includes(q));
  }, [tables, search]);

  const handleSelect = (t: MartTable) => {
    setSelectedTable(t);
    if (!name.trim()) setName(t.name);
  };

  const handleSubmit = async () => {
    if (!selectedTable) {
      toast({
        title: 'Pick a table',
        description: 'Select a mart table to base the dataset on.',
        variant: 'destructive',
      });
      return;
    }
    if (!name.trim()) {
      toast({
        title: 'Name is required',
        variant: 'destructive',
      });
      return;
    }
    try {
      const ds = await createDataset.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        kind: 'physical',
        source: 'manual',
        database_name: martDb,
        schema: martDb,
        table_name: selectedTable.name,
        columns: selectedTable.columns.map((c, i) => ({
          column_name: c.name,
          type: c.type,
          column_order: i,
          is_dttm: /date|time/i.test(c.type),
          is_active: true,
          groupby: true,
          filterable: true,
          is_hidden: false,
        })),
      });
      toast({
        title: 'Dataset created',
        description: `${ds.name} is ready to use in charts.`,
      });
      navigate(`/app/datasets/${ds.id}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to create dataset';
      toast({
        title: 'Create failed',
        description: message,
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <PageHeader
        title="New dataset"
        description="Create a reusable dataset from your tenant's curated mart layer."
        icon={<Database className="h-6 w-6" />}
        actions={
          <Button variant="outline" onClick={() => navigate('/app/datasets')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to datasets
          </Button>
        }
      />

      {/* Locked DB indicator */}
      <Card>
        <CardContent className="p-4 flex items-center gap-3">
          <Lock className="h-4 w-4 text-muted-foreground" />
          <div className="text-sm">
            <span className="text-muted-foreground">Source database (locked):</span>{' '}
            {martQuery.isLoading ? (
              <Skeleton className="inline-block h-4 w-48 align-middle" />
            ) : (
              <code className="font-mono font-medium">{martDb || '—'}</code>
            )}
          </div>
          <Badge variant="secondary" className="ml-auto">
            mart layer
          </Badge>
        </CardContent>
      </Card>

      {martQuery.isError && (
        <Card className="border-destructive">
          <CardContent className="p-4 flex items-start gap-3 text-sm">
            <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
            <div>
              <div className="font-medium">Failed to load mart tables</div>
              <div className="text-muted-foreground">
                {(martQuery.error as Error)?.message ?? 'Unknown error'}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {!martQuery.isLoading && !martQuery.isError && !martExists && (
        <Card className="border-amber-500/50">
          <CardContent className="p-4 flex items-start gap-3 text-sm">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div>
              <div className="font-medium">No mart tables yet</div>
              <div className="text-muted-foreground">
                The mart database <code className="font-mono">{martDb}</code> hasn't
                been materialized. Run a dbt build that targets the marts layer,
                then come back here.
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table picker */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Pick a mart table</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search tables…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {martQuery.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : filteredTables.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-12">
                {tables.length === 0
                  ? 'No tables in the mart database yet.'
                  : 'No tables match your search.'}
              </div>
            ) : (
              <div className="border rounded-md divide-y max-h-[480px] overflow-auto">
                {filteredTables.map((t) => {
                  const active = selectedTable?.name === t.name;
                  return (
                    <button
                      key={t.name}
                      type="button"
                      onClick={() => handleSelect(t)}
                      className={`w-full text-left p-3 flex items-center gap-3 hover:bg-muted/60 transition-colors ${
                        active ? 'bg-primary/10' : ''
                      }`}
                    >
                      <Table2 className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{t.name}</div>
                        <div className="text-xs text-muted-foreground flex items-center gap-2">
                          <span>{t.engine}</span>
                          {typeof t.total_rows === 'number' && (
                            <>
                              <span>•</span>
                              <span>{t.total_rows.toLocaleString()} rows</span>
                            </>
                          )}
                          <span>•</span>
                          <span>{t.columns.length} columns</span>
                        </div>
                      </div>
                      {active && (
                        <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dataset details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="ds-name">Name *</Label>
              <Input
                id="ds-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Monthly active users"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ds-desc">Description</Label>
              <Textarea
                id="ds-desc"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does this dataset represent?"
              />
            </div>

            <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
              <div>
                <span className="text-muted-foreground">Database:</span>{' '}
                <code className="font-mono">{martDb || '—'}</code>
              </div>
              <div>
                <span className="text-muted-foreground">Table:</span>{' '}
                <code className="font-mono">
                  {selectedTable?.name ?? 'Not selected'}
                </code>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => navigate('/app/datasets')}
                disabled={createDataset.isPending}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={handleSubmit}
                disabled={
                  createDataset.isPending ||
                  !selectedTable ||
                  !name.trim() ||
                  !martExists
                }
              >
                {createDataset.isPending && (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                )}
                Create dataset
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
