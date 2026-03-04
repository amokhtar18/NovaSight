/**
 * NovaSight Scheduling Page
 * =========================
 *
 * Unified page for managing and monitoring Dagster jobs and runs.
 * Combines job management with Dagster orchestration monitoring.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobService, Job } from '@/services/jobService'
import { dagsterService } from '@/services/dagsterService'
import {
  AssetGraph,
  ScheduleList,
  SensorList,
  RunsList,
  InstanceStatus,
} from '@/components/dagster'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Plus,
  Play,
  Pause,
  Eye,
  Settings,
  Loader2,
  Trash2,
  MoreVertical,
  Zap,
  GitBranch,
  Search,
  RefreshCw,
  ArrowRight,
  Activity,
  Calendar,
  Radio,
  ExternalLink,
  XCircle,
  Briefcase,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from '@/components/ui/use-toast'
import { getStatusClasses } from '@/lib/colors'

export function SchedulingPage() {
  const queryClient = useQueryClient()
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [selectedAssetKey, setSelectedAssetKey] = useState<string[] | null>(null)

  // Fetch jobs
  const {
    data: jobsData,
    isLoading: jobsLoading,
    error: jobsError,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: ['jobs', statusFilter, typeFilter],
    queryFn: () =>
      jobService.list({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type: typeFilter !== 'all' ? (typeFilter as 'spark' | 'pipeline') : undefined,
        per_page: 50,
      }),
    refetchInterval: 30000,
  })

  // Dagster stats queries
  const { data: runs } = useQuery({
    queryKey: ['dagster-runs-stats'],
    queryFn: () => dagsterService.getRuns(undefined, 100),
    refetchInterval: 10000,
  })

  const { data: schedules } = useQuery({
    queryKey: ['dagster-schedules'],
    queryFn: () => dagsterService.getSchedules(),
    refetchInterval: 30000,
  })

  const { data: sensors } = useQuery({
    queryKey: ['dagster-sensors'],
    queryFn: () => dagsterService.getSensors(),
    refetchInterval: 30000,
  })

  const { data: assets } = useQuery({
    queryKey: ['dagster-assets'],
    queryFn: () => dagsterService.getAssets(),
    refetchInterval: 30000,
  })

  // Calculate stats
  const runningCount = runs?.filter((r) => r.status === 'running').length || 0
  const queuedCount = runs?.filter((r) => r.status === 'queued').length || 0
  const recentFailures = runs?.filter((r) => r.status === 'failed').length || 0
  const activeSchedules = schedules?.filter((s) => s.scheduleState?.status === 'RUNNING').length || 0
  const activeSensors = sensors?.filter((s) => s.sensorState?.status === 'RUNNING').length || 0

  // Mutations
  const triggerMutation = useMutation({
    mutationFn: (jobId: string) => jobService.trigger(jobId),
    onSuccess: (result, _jobId) => {
      if (result.success) {
        toast({
          title: 'Job Triggered',
          description: `Run started: ${result.run_id}`,
        })
        queryClient.invalidateQueries({ queryKey: ['jobs'] })
      } else {
        toast({
          title: 'Trigger Failed',
          description: result.error || 'Unknown error',
          variant: 'destructive',
        })
      }
    },
    onError: (err: unknown) => {
      // Extract error message from API response
      let message = 'Failed to trigger job'
      if (err && typeof err === 'object') {
        const axiosErr = err as { response?: { data?: { error?: { message?: string } } }; message?: string }
        if (axiosErr.response?.data?.error?.message) {
          message = axiosErr.response.data.error.message
        } else if (axiosErr.message) {
          message = axiosErr.message
        }
      }
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      })
    },
  })

  const pauseMutation = useMutation({
    mutationFn: (jobId: string) => jobService.pause(jobId),
    onSuccess: () => {
      toast({ title: 'Job Paused' })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const resumeMutation = useMutation({
    mutationFn: (jobId: string) => jobService.resume(jobId),
    onSuccess: () => {
      toast({ title: 'Job Resumed' })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => jobService.delete(jobId),
    onSuccess: () => {
      toast({ title: 'Job Deleted' })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setDeleteTarget(null)
    },
  })

  // Filter jobs by search query
  const filteredJobs = (jobsData?.items || []).filter((job) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      job.dag_id.toLowerCase().includes(query) ||
      job.description?.toLowerCase().includes(query) ||
      job.tags.some((tag) => tag.toLowerCase().includes(query))
    )
  })

  const handleTogglePause = (job: Job) => {
    if (job.status === 'active') {
      pauseMutation.mutate(job.id)
    } else if (job.status === 'paused') {
      resumeMutation.mutate(job.id)
    }
  }

  const handleOpenDagsterUI = () => {
    window.open('http://localhost:3000', '_blank')
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      draft: 'outline',
      active: 'default',
      paused: 'secondary',
      archived: 'destructive',
    }
    const variant = variants[status] || 'outline'
    return (
      <Badge variant={variant} className={getStatusClasses(status)}>
        {status}
      </Badge>
    )
  }

  const getTypeBadge = (type: string) => {
    if (type === 'pipeline') {
      return (
        <Badge variant="outline" className="border-purple-400 text-purple-600">
          <GitBranch className="mr-1 h-3 w-3" />
          Pipeline
        </Badge>
      )
    }
    return (
      <Badge variant="outline" className="border-orange-400 text-orange-600">
        <Zap className="mr-1 h-3 w-3" />
        Spark
      </Badge>
    )
  }

  const getScheduleDisplay = (job: Job) => {
    if (job.schedule_type === 'manual') {
      return 'Manual'
    }
    if (job.schedule_type === 'preset') {
      const preset = job.schedule_preset?.replace('@', '') || ''
      return preset ? preset.charAt(0).toUpperCase() + preset.slice(1) : 'Preset'
    }
    return job.schedule_cron || 'Custom'
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Scheduling</h1>
          <p className="text-muted-foreground">
            Manage jobs, monitor runs, and control orchestration
          </p>
        </div>
        <div className="flex items-center gap-4">
          <InstanceStatus compact />
          <Button variant="outline" onClick={handleOpenDagsterUI}>
            <ExternalLink className="mr-2 h-4 w-4" />
            Dagster UI
          </Button>
          <Button asChild>
            <Link to="/app/jobs/new">
              <Plus className="mr-2 h-4 w-4" />
              Create Job
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Jobs</p>
                <p className="text-2xl font-bold">{jobsData?.items?.length || 0}</p>
              </div>
              <Briefcase className="h-8 w-8 text-muted-foreground opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Running</p>
                <p className="text-2xl font-bold text-blue-600">{runningCount}</p>
              </div>
              <Activity className="h-8 w-8 text-blue-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Queued</p>
                <p className="text-2xl font-bold text-yellow-600">{queuedCount}</p>
              </div>
              <Activity className="h-8 w-8 text-yellow-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Failures</p>
                <p className="text-2xl font-bold text-red-600">{recentFailures}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Schedules</p>
                <p className="text-2xl font-bold text-green-600">
                  {activeSchedules}/{schedules?.length || 0}
                </p>
              </div>
              <Calendar className="h-8 w-8 text-green-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Sensors</p>
                <p className="text-2xl font-bold text-purple-600">
                  {activeSensors}/{sensors?.length || 0}
                </p>
              </div>
              <Radio className="h-8 w-8 text-purple-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="jobs" className="space-y-4">
        <TabsList>
          <TabsTrigger value="jobs" className="flex items-center gap-2">
            <Briefcase className="h-4 w-4" />
            Jobs
          </TabsTrigger>
          <TabsTrigger value="runs" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Runs
          </TabsTrigger>
          <TabsTrigger value="assets" className="flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            Assets
          </TabsTrigger>
          <TabsTrigger value="schedules" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Schedules
          </TabsTrigger>
          <TabsTrigger value="sensors" className="flex items-center gap-2">
            <Radio className="h-4 w-4" />
            Sensors
          </TabsTrigger>
        </TabsList>

        {/* Jobs Tab */}
        <TabsContent value="jobs" className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="spark">Spark Jobs</SelectItem>
                <SelectItem value="pipeline">Pipelines</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="ghost" size="icon" onClick={() => refetchJobs()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* Jobs Grid */}
          {jobsLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : jobsError ? (
            <div className="flex h-64 flex-col items-center justify-center gap-4">
              <p className="text-destructive">Failed to load jobs</p>
              <Button variant="outline" onClick={() => refetchJobs()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            </div>
          ) : filteredJobs.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredJobs.map((job) => (
                <Card key={job.id} className="hover:shadow-md transition-shadow">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg truncate" title={job.dag_id}>
                        {job.dag_id}
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        {getTypeBadge(job.type)}
                        {getStatusBadge(job.status)}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-4 h-10">
                      {job.description || 'No description'}
                    </p>

                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Schedule:</span>
                        <span className="font-medium">{getScheduleDisplay(job)}</span>
                      </div>
                      {job.last_run && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Last Run:</span>
                          <span className="font-medium">
                            <Badge
                              variant={
                                job.last_run.status === 'SUCCESS'
                                  ? 'default'
                                  : job.last_run.status === 'FAILURE'
                                  ? 'destructive'
                                  : 'secondary'
                              }
                              className="text-xs"
                            >
                              {job.last_run.status}
                            </Badge>
                          </span>
                        </div>
                      )}
                      {job.deployed_at && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Updated:</span>
                          <span className="font-medium text-xs">
                            {formatDistanceToNow(new Date(job.updated_at))} ago
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="mt-4 flex items-center gap-2">
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => triggerMutation.mutate(job.id)}
                        disabled={triggerMutation.isPending || job.status === 'archived'}
                      >
                        {triggerMutation.isPending ? (
                          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                          <Play className="mr-1 h-3 w-3" />
                        )}
                        Run
                      </Button>
                      <Button variant="outline" size="sm" asChild>
                        <Link to={`/app/jobs/${job.id}`}>
                          <Eye className="mr-1 h-3 w-3" />
                          View
                        </Link>
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link to={`/app/jobs/${job.id}/edit`}>
                              <Settings className="mr-2 h-4 w-4" />
                              Edit
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem asChild>
                            <Link to={`/app/jobs/${job.id}/runs`}>
                              <ArrowRight className="mr-2 h-4 w-4" />
                              View Runs
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          {job.status === 'active' ? (
                            <DropdownMenuItem onClick={() => handleTogglePause(job)}>
                              <Pause className="mr-2 h-4 w-4" />
                              Pause
                            </DropdownMenuItem>
                          ) : job.status === 'paused' ? (
                            <DropdownMenuItem onClick={() => handleTogglePause(job)}>
                              <Play className="mr-2 h-4 w-4" />
                              Resume
                            </DropdownMenuItem>
                          ) : null}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeleteTarget(job)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Zap className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No Jobs Found</h3>
                <p className="text-muted-foreground text-center mb-4">
                  {searchQuery
                    ? 'No jobs match your search criteria'
                    : "You haven't created any Spark jobs yet"}
                </p>
                <Button asChild>
                  <Link to="/app/jobs/new">
                    <Plus className="mr-2 h-4 w-4" />
                    Create Your First Job
                  </Link>
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Runs Tab */}
        <TabsContent value="runs">
          <RunsList
            limit={50}
            onRunSelect={setSelectedRunId}
          />
        </TabsContent>

        {/* Assets Tab */}
        <TabsContent value="assets">
          <AssetGraph
            onAssetSelect={setSelectedAssetKey}
            selectedAssetKey={selectedAssetKey}
            className="min-h-[600px]"
          />
        </TabsContent>

        {/* Schedules Tab */}
        <TabsContent value="schedules">
          <ScheduleList />
        </TabsContent>

        {/* Sensors Tab */}
        <TabsContent value="sensors">
          <SensorList />
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Job</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteTarget?.dag_id}"? This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Run Details Sheet */}
      <RunDetailsSheet
        runId={selectedRunId}
        open={!!selectedRunId}
        onClose={() => setSelectedRunId(null)}
      />

      {/* Asset Details Sheet */}
      <AssetDetailsSheet
        assetKey={selectedAssetKey}
        open={!!selectedAssetKey}
        onClose={() => setSelectedAssetKey(null)}
      />
    </div>
  )
}

// Run Details Sheet Component
function RunDetailsSheet({
  runId,
  open,
  onClose,
}: {
  runId: string | null
  open: boolean
  onClose: () => void
}) {
  const {
    data: run,
    isLoading,
  } = useQuery({
    queryKey: ['dagster-run-details', runId],
    queryFn: () => (runId ? dagsterService.getRunDetails(runId) : null),
    enabled: !!runId,
  })

  const {
    data: logs,
  } = useQuery({
    queryKey: ['dagster-run-logs', runId],
    queryFn: () => (runId ? dagsterService.getRunLogs(runId) : null),
    enabled: !!runId,
    refetchInterval: run?.status === 'STARTED' ? 2000 : false,
  })

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[600px] sm:max-w-[600px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            Run Details
            {runId && (
              <code className="text-sm font-mono bg-muted px-2 py-0.5 rounded">
                {runId.substring(0, 8)}
              </code>
            )}
          </SheetTitle>
          <SheetDescription>
            {run ? `Job: ${run.pipelineName}` : 'Loading...'}
          </SheetDescription>
        </SheetHeader>

        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : run ? (
          <div className="mt-4 space-y-4">
            {/* Run Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge
                  variant="outline"
                  className={getStatusClasses(run.status)}
                >
                  {run.status}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Mode</p>
                <p className="font-medium">{run.mode}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Started</p>
                <p className="text-sm">
                  {run.startTime
                    ? new Date(run.startTime * 1000).toLocaleString()
                    : '-'}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Ended</p>
                <p className="text-sm">
                  {run.endTime
                    ? new Date(run.endTime * 1000).toLocaleString()
                    : '-'}
                </p>
              </div>
            </div>

            {/* Tags */}
            {run.tags && run.tags.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">Tags</p>
                <div className="flex flex-wrap gap-1">
                  {run.tags.map((tag, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {tag.key}: {tag.value}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Logs */}
            <div>
              <p className="text-sm text-muted-foreground mb-2">Logs</p>
              <ScrollArea className="h-[300px] rounded-md border bg-muted/50 p-2">
                {logs?.events.length ? (
                  <div className="space-y-1 font-mono text-xs">
                    {logs.events.map((event, idx) => (
                      <div
                        key={idx}
                        className={`py-0.5 ${
                          event.level === 'ERROR'
                            ? 'text-red-600'
                            : event.level === 'WARNING'
                            ? 'text-yellow-600'
                            : 'text-foreground'
                        }`}
                      >
                        <span className="text-muted-foreground">
                          [{new Date(event.timestamp).toLocaleTimeString()}]
                        </span>{' '}
                        {event.stepKey && (
                          <span className="text-blue-600">[{event.stepKey}]</span>
                        )}{' '}
                        {event.message}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No logs available
                  </p>
                )}
              </ScrollArea>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() =>
                  window.open(`http://localhost:3000/runs/${runId}`, '_blank')
                }
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                View in Dagster
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex h-64 items-center justify-center">
            <p className="text-muted-foreground">Run not found</p>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

// Asset Details Sheet Component
function AssetDetailsSheet({
  assetKey,
  open,
  onClose,
}: {
  assetKey: string[] | null
  open: boolean
  onClose: () => void
}) {
  const {
    data: asset,
    isLoading,
  } = useQuery({
    queryKey: ['dagster-asset-details', assetKey],
    queryFn: () => (assetKey ? dagsterService.getAssetDetails(assetKey) : null),
    enabled: !!assetKey,
  })

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[500px] sm:max-w-[500px]">
        <SheetHeader>
          <SheetTitle>Asset Details</SheetTitle>
          <SheetDescription>
            {assetKey?.join(' → ') || 'Loading...'}
          </SheetDescription>
        </SheetHeader>

        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : asset ? (
          <div className="mt-4 space-y-4">
            {/* Asset Info */}
            <div className="space-y-3">
              {asset.description && (
                <div>
                  <p className="text-sm text-muted-foreground">Description</p>
                  <p className="text-sm">{asset.description}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Group</p>
                  <Badge variant="secondary">{asset.groupName || 'default'}</Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Compute Kind</p>
                  <Badge variant="outline">{asset.computeKind || 'N/A'}</Badge>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Type</p>
                  <p className="text-sm">
                    {asset.isSource ? 'Source Asset' : 'Computed Asset'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Partitioned</p>
                  <p className="text-sm">{asset.isPartitioned ? 'Yes' : 'No'}</p>
                </div>
              </div>

              {/* Last Materialization */}
              {asset.latestMaterialization && (
                <div>
                  <p className="text-sm text-muted-foreground">Last Materialized</p>
                  <p className="text-sm">
                    {new Date(asset.latestMaterialization.timestamp).toLocaleString()}
                  </p>
                </div>
              )}
            </div>

            {/* Dependencies */}
            {asset.dependencyKeys && asset.dependencyKeys.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">
                  Dependencies ({asset.dependencyKeys.length})
                </p>
                <div className="flex flex-wrap gap-1">
                  {asset.dependencyKeys.map((key, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {key.path.join(' → ')}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Dependents */}
            {asset.dependedByKeys && asset.dependedByKeys.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">
                  Dependents ({asset.dependedByKeys.length})
                </p>
                <div className="flex flex-wrap gap-1">
                  {asset.dependedByKeys.map((key, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {key.path.join(' → ')}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  const keyPath = assetKey?.join('/') || ''
                  window.open(
                    `http://localhost:3000/assets/${encodeURIComponent(keyPath)}`,
                    '_blank'
                  )
                }}
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                View in Dagster
              </Button>
              {asset.hasMaterializePermission && !asset.isSource && (
                <Button>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Materialize
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex h-64 items-center justify-center">
            <p className="text-muted-foreground">Asset not found</p>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

export default SchedulingPage
