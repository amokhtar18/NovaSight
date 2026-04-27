/**
 * Pipeline List Component
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Plus,
  Search,
  Play,
  Pause,
  Trash2,
  MoreVertical,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Database,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import {
  usePipelines,
  useActivatePipeline,
  useDeactivatePipeline,
  useDeletePipeline,
  useRunPipeline,
} from '../hooks'
import type { Pipeline, PipelineStatus } from '@/types/pipeline'

const STATUS_BADGES: Record<PipelineStatus, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: React.ReactNode }> = {
  draft: { variant: 'secondary', icon: <Clock className="h-3 w-3" /> },
  active: { variant: 'default', icon: <CheckCircle className="h-3 w-3" /> },
  inactive: { variant: 'outline', icon: <Pause className="h-3 w-3" /> },
  error: { variant: 'destructive', icon: <XCircle className="h-3 w-3" /> },
}

export function PipelineList() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data, isLoading, refetch } = usePipelines({
    search: search || undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
  })

  const activateMutation = useActivatePipeline()
  const deactivateMutation = useDeactivatePipeline()
  const deleteMutation = useDeletePipeline()
  const runMutation = useRunPipeline()

  const handleActivate = async (pipeline: Pipeline) => {
    try {
      await activateMutation.mutateAsync(pipeline.id)
      toast({
        title: 'Pipeline activated',
        description: `${pipeline.name} is now active.`,
      })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to activate pipeline'
      toast({ title: 'Error', description: message, variant: 'destructive' })
    }
  }

  const handleDeactivate = async (pipeline: Pipeline) => {
    try {
      await deactivateMutation.mutateAsync(pipeline.id)
      toast({
        title: 'Pipeline deactivated',
        description: `${pipeline.name} is now inactive.`,
      })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to deactivate pipeline'
      toast({ title: 'Error', description: message, variant: 'destructive' })
    }
  }

  const handleDelete = async (pipeline: Pipeline) => {
    if (!confirm(`Are you sure you want to delete "${pipeline.name}"?`)) return
    try {
      await deleteMutation.mutateAsync(pipeline.id)
      toast({
        title: 'Pipeline deleted',
        description: `${pipeline.name} has been deleted.`,
      })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to delete pipeline'
      toast({ title: 'Error', description: message, variant: 'destructive' })
    }
  }

  const handleRun = async (pipeline: Pipeline) => {
    try {
      const result = await runMutation.mutateAsync(pipeline.id)
      toast({
        title: 'Pipeline run triggered',
        description: result.message,
      })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to run pipeline'
      toast({ title: 'Error', description: message, variant: 'destructive' })
    }
  }

  const formatDuration = (ms?: number) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
  }

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Data Pipelines</h1>
          <p className="text-muted-foreground">
            Extract data from sources into your Iceberg data lake
          </p>
        </div>
        <Button onClick={() => navigate('/app/pipelines/new')}>
          <Plus className="h-4 w-4 mr-2" />
          Create Pipeline
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search pipelines..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Pipeline Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : data?.items?.length === 0 ? (
        <Card className="p-8 text-center">
          <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No pipelines yet</h3>
          <p className="text-muted-foreground mb-4">
            Create your first data pipeline to start extracting data.
          </p>
          <Button onClick={() => navigate('/app/pipelines/new')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Pipeline
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items?.map((pipeline) => {
            const statusConfig = STATUS_BADGES[pipeline.status]
            
            return (
              <Card key={pipeline.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <Link to={`/app/pipelines/${pipeline.id}`}>
                        <CardTitle className="hover:underline cursor-pointer">
                          {pipeline.name}
                        </CardTitle>
                      </Link>
                      <CardDescription className="line-clamp-2 mt-1">
                        {pipeline.description || 'No description'}
                      </CardDescription>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {pipeline.status === 'active' ? (
                          <DropdownMenuItem onClick={() => handleDeactivate(pipeline)}>
                            <Pause className="h-4 w-4 mr-2" />
                            Deactivate
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem onClick={() => handleActivate(pipeline)}>
                            <Play className="h-4 w-4 mr-2" />
                            Activate
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                          onClick={() => handleRun(pipeline)}
                          disabled={pipeline.status !== 'active'}
                        >
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Run Now
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => handleDelete(pipeline)}
                          className="text-destructive"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={statusConfig.variant}>
                      {statusConfig.icon}
                      <span className="ml-1 capitalize">{pipeline.status}</span>
                    </Badge>
                    <Badge variant="outline" className="capitalize">
                      {pipeline.write_disposition}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <p>Source: {pipeline.source_type === 'table' 
                      ? `${pipeline.source_schema}.${pipeline.source_table}`
                      : 'Query'
                    }</p>
                    <p>Target: {pipeline.iceberg_table_name || pipeline.name}</p>
                  </div>
                </CardContent>
                <CardFooter className="text-xs text-muted-foreground">
                  <div className="flex items-center justify-between w-full">
                    <span>Last run: {formatDate(pipeline.last_run_at)}</span>
                    {pipeline.last_run_duration_ms && (
                      <span>{formatDuration(pipeline.last_run_duration_ms)}</span>
                    )}
                  </div>
                </CardFooter>
              </Card>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <span className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} ({data.total} total)
          </span>
        </div>
      )}
    </div>
  )
}
