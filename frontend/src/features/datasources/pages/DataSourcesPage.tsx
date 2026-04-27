import { useMemo, useState } from 'react'
import {
  Plus,
  Search,
  Filter,
  Database,
  CheckCircle2,
  AlertCircle,
  Layers,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DataSourceCard } from '../components/DataSourceCard'
import { ConnectionWizard } from '../components/ConnectionWizard'
import { useDataSources } from '../hooks'
import {
  DATABASE_TYPES,
  type DatabaseType,
  type DataSource,
} from '@/types/datasource'
import { Skeleton } from '@/components/ui/skeleton'

type CategoryTab = 'all' | 'database'

interface StatProps {
  label: string
  value: number | string
  icon: React.ComponentType<{ className?: string }>
  tone?: 'default' | 'success' | 'warning' | 'destructive'
}

function StatCard({ label, value, icon: Icon, tone = 'default' }: StatProps) {
  const toneClasses = {
    default: 'bg-primary/10 text-primary',
    success: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    destructive: 'bg-destructive/10 text-destructive',
  }[tone]

  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card p-4">
      <div className={`p-2.5 rounded-lg ${toneClasses}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-semibold leading-tight">{value}</p>
      </div>
    </div>
  )
}

export function DataSourcesPage() {
  const [wizardOpen, setWizardOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<DatabaseType | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [categoryTab, setCategoryTab] = useState<CategoryTab>('all')

  const { data, isLoading, isFetching, refetch } = useDataSources({
    db_type: typeFilter !== 'all' ? typeFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
  })

  const items: DataSource[] = data?.items ?? []

  const stats = useMemo(() => {
    return {
      total: data?.total ?? items.length,
      active: items.filter((d) => d.status === 'active').length,
      errors: items.filter((d) => d.status === 'error').length,
      databases: items.length,
    }
  }, [items, data?.total])

  const filteredDataSources = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return items.filter((ds) => {
      if (!q) return true
      const haystack = [
        ds.name,
        ds.host ?? '',
        ds.database ?? '',
        ds.schema_name ?? '',
        DATABASE_TYPES[ds.db_type]?.name ?? '',
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(q)
    })
  }, [items, searchQuery])

  const hasFilters =
    searchQuery !== '' ||
    typeFilter !== 'all' ||
    statusFilter !== 'all' ||
    categoryTab !== 'all'

  const clearFilters = () => {
    setSearchQuery('')
    setTypeFilter('all')
    setStatusFilter('all')
    setCategoryTab('all')
  }

  return (
    <div className="container py-8 space-y-6 max-w-screen-2xl">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
          <p className="text-muted-foreground mt-1">
            Connect databases and files, then trigger ingestion into the lake.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            disabled={isFetching}
            title="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={() => setWizardOpen(true)} size="lg">
            <Plus className="h-5 w-5 mr-2" />
            Connect Data Source
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <StatCard label="Total" value={stats.total} icon={Layers} />
        <StatCard label="Active" value={stats.active} icon={CheckCircle2} tone="success" />
        <StatCard label="Databases" value={stats.databases} icon={Database} />
      </div>

      {/* Tabs + filters */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Tabs value={categoryTab} onValueChange={(v) => setCategoryTab(v as CategoryTab)}>
          <TabsList>
            <TabsTrigger value="all">
              All
              <span className="ml-1.5 text-xs text-muted-foreground">{items.length}</span>
            </TabsTrigger>
            <TabsTrigger value="database">
              <Database className="h-3.5 w-3.5 mr-1.5" />
              Databases
              <span className="ml-1.5 text-xs text-muted-foreground">{stats.databases}</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name, host, file…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value as DatabaseType | 'all')}>
            <SelectTrigger className="w-full sm:w-[160px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="All types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {Object.values(DATABASE_TYPES).map((type) => (
                <SelectItem key={type.type} value={type.type}>
                  {type.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-[140px]">
              <SelectValue placeholder="All status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Result summary */}
      {!isLoading && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Showing {filteredDataSources.length} of {items.length} data source
            {items.length !== 1 ? 's' : ''}
          </span>
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-[220px] rounded-lg" />
          ))}
        </div>
      ) : filteredDataSources.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredDataSources.map((datasource) => (
            <DataSourceCard key={datasource.id} datasource={datasource} />
          ))}
        </div>
      ) : items.length === 0 ? (
        // True empty state — no data sources at all
        <div className="flex flex-col items-center justify-center py-16 text-center border-2 border-dashed rounded-xl bg-muted/20">
          <div className="p-4 rounded-full bg-primary/10 mb-4">
            <Database className="h-10 w-10 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No data sources yet</h3>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Connect a database or upload a flat file to start exploring and ingesting your data
            into the lake.
          </p>
          <div className="flex flex-wrap items-center gap-2 justify-center">
            <Button onClick={() => setWizardOpen(true)} size="lg">
              <Plus className="h-4 w-4 mr-2" />
              Connect Data Source
            </Button>
          </div>
        </div>
      ) : (
        // Filtered empty state
        <div className="flex flex-col items-center justify-center py-12 text-center border rounded-lg bg-muted/10">
          <AlertCircle className="h-8 w-8 text-muted-foreground mb-3" />
          <h3 className="text-lg font-semibold mb-1">No matches</h3>
          <p className="text-sm text-muted-foreground mb-4">
            No data sources match your current filters.
          </p>
          <Button variant="outline" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        </div>
      )}

      {/* Connection Wizard */}
      <ConnectionWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onSuccess={() => refetch()}
      />
    </div>
  )
}
