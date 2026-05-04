/**
 * NovaSight Scheduling Page
 * =========================
 *
 * Unified scheduling page that merges dlt pipelines and orchestration jobs
 * into a single table. Each row represents a pipeline (or standalone dbt
 * job) and surfaces its schedule configuration directly, with the option
 * to configure a schedule, run it manually, pause/resume, or remove it.
 *
 * Run history views have been removed — operators monitor live state via
 * the Dagster UI link.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobService, Job } from '@/services/jobService'
import { dagsterService } from '@/services/dagsterService'
import { pipelineService } from '@/services/pipelineService'
import type { Pipeline } from '@/types/pipeline'
import {
  AssetGraph,
  SensorList,
  InstanceStatus,
} from '@/components/dagster'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/common'
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
  Plus,
  Play,
  Pause,
  Eye,
  Settings,
  Loader2,
  Trash2,
  MoreVertical,
  GitBranch,
  Code2,
  Search,
  RefreshCw,
  Calendar,
  CalendarOff,
  Radio,
  ExternalLink,
  XCircle,
  Briefcase,
  Database,
  Activity,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from '@/components/ui/use-toast'
import { getStatusClasses } from '@/lib/colors'

// =============================================================================
// Types
// =============================================================================

type EntityType = 'pipeline' | 'dbt_run' | 'dbt_test'

interface UnifiedRow {
  id: string                  // Stable row id (pipeline id or job id)
  name: string
  description?: string
  entityType: EntityType
  pipeline?: Pipeline
  job?: Job
  source?: string             // For pipelines: source table; for dbt jobs: dag_id
  scheduleLabel: string       // e.g. "Daily", "0 5 * * *", "No schedule"
  isScheduled: boolean
  status: string              // active | paused | draft | no-schedule
  lastRun?: { status: string; at?: string }
}

// =============================================================================
// Component
// =============================================================================

export function SchedulingPage() {
  const queryClient = useQueryClient()
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  // typeFilter is preserved for jobService.list filter shape (no UI control any more)
  const [typeFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAssetKey, setSelectedAssetKey] = useState<string[] | null>(null)

  // ── Data ────────────────────────────────────────────────────────────────
  const {
    data: jobsData,
    isLoading: jobsLoading,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: ['jobs', statusFilter, typeFilter],
    queryFn: () =>
      jobService.list({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type:
          typeFilter !== 'all'
            ? (typeFilter as 'dlt' | 'dbt' | 'pipeline')
            : undefined,
        per_page: 200,
      }),
    refetchInterval: 30000,
  })

  const {
    data: pipelinesData,
    isLoading: pipelinesLoading,
    refetch: refetchPipelines,
  } = useQuery({
    queryKey: ['pipelines-for-scheduling'],
    queryFn: () => pipelineService.list({ per_page: 200 }),
    refetchInterval: 30000,
  })

  const { data: runs } = useQuery({
    queryKey: ['dagster-runs-stats'],
    queryFn: () => dagsterService.getRuns(undefined, 100),
    refetchInterval: 15000,
  })

  const { data: schedules } = useQuery({
    queryKey: ['dagster-schedules'],
    queryFn: () => dagsterService.getSchedules(),
    refetchInterval: 30000,
  })

  // ── Stats ───────────────────────────────────────────────────────────────
  const runningCount = runs?.filter((r) => r.status === 'running').length || 0
  const queuedCount = runs?.filter((r) => r.status === 'queued').length || 0
  const recentFailures = runs?.filter((r) => r.status === 'failed').length || 0
  const activeSchedules =
    schedules?.filter((s) => s.scheduleState?.status === 'RUNNING').length || 0

  // ── Mutations ───────────────────────────────────────────────────────────
  const triggerMutation = useMutation({
    mutationFn: (jobId: string) => jobService.trigger(jobId),
    onSuccess: (result) => {
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
      let message = 'Failed to trigger job'
      if (err && typeof err === 'object') {
        const axiosErr = err as {
          response?: { data?: { error?: { message?: string } } }
          message?: string
        }
        message =
          axiosErr.response?.data?.error?.message || axiosErr.message || message
      }
      toast({ title: 'Error', description: message, variant: 'destructive' })
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
      toast({ title: 'Schedule Removed' })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setDeleteTarget(null)
    },
  })

  // ── Helpers ─────────────────────────────────────────────────────────────
  const getScheduleDisplay = (job?: Job) => {
    if (!job) return 'No schedule'
    if (job.schedule_type === 'manual') return 'Manual'
    if (job.schedule_type === 'preset') {
      const preset = job.schedule_preset?.replace('@', '') || ''
      return preset
        ? preset.charAt(0).toUpperCase() + preset.slice(1)
        : 'Preset'
    }
    return job.schedule_cron || 'Custom'
  }

  const findJobForPipeline = (pipelineId: string): Job | undefined => {
    const items = jobsData?.items || []
    return items.find(
      (j) =>
        j.tags.includes(pipelineId) &&
        (j.type === 'dlt' || j.type === 'pipeline'),
    )
  }

  const handleTogglePause = (job: Job) => {
    if (job.status === 'active') pauseMutation.mutate(job.id)
    else if (job.status === 'paused') resumeMutation.mutate(job.id)
  }

  const handleOpenDagsterUI = () => {
    window.open('http://localhost:3000', '_blank')
  }

  // ── Build unified rows: pipelines + standalone dbt jobs ─────────────────
  const unifiedRows = useMemo<UnifiedRow[]>(() => {
    const pipelines = pipelinesData?.items || []
    const jobs = jobsData?.items || []

    const rows: UnifiedRow[] = []

    // 1) Each pipeline becomes a row (with linked job if scheduled)
    for (const p of pipelines) {
      const job = findJobForPipeline(p.id)
      rows.push({
        id: p.id,
        name: p.name,
        description: p.description,
        entityType: 'pipeline',
        pipeline: p,
        job,
        source:
          p.source_table ||
          p.iceberg_table_name ||
          p.source_query ||
          undefined,
        scheduleLabel: getScheduleDisplay(job),
        isScheduled: !!job && job.schedule_type !== 'manual',
        status: job ? job.status : 'no-schedule',
        lastRun: p.last_run_status
          ? { status: p.last_run_status, at: p.last_run_at }
          : job?.last_run
          ? { status: job.last_run.status, at: job.last_run.start_time }
          : undefined,
      })
    }

    // 2) Standalone dbt jobs (no pipeline binding) split by kind
    for (const j of jobs) {
      if (j.type !== 'dbt') continue
      const isTest = j.tags.includes('dbt_test')
      rows.push({
        id: j.id,
        name: j.dag_id,
        description: j.description,
        entityType: isTest ? 'dbt_test' : 'dbt_run',
        job: j,
        source: j.dag_id,
        scheduleLabel: getScheduleDisplay(j),
        isScheduled: j.schedule_type !== 'manual',
        status: j.status,
        lastRun: j.last_run
          ? { status: j.last_run.status, at: j.last_run.start_time }
          : undefined,
      })
    }

    return rows
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipelinesData, jobsData])

  const filteredRows = useMemo(() => {
    return unifiedRows.filter((r) => {
      if (typeFilter !== 'all') {
        if (typeFilter === 'pipeline' && r.entityType !== 'pipeline') return false
        if (
          typeFilter === 'dbt' &&
          r.entityType !== 'dbt_run' &&
          r.entityType !== 'dbt_test'
        )
          return false
      }
      if (statusFilter !== 'all') {
        if (statusFilter === 'scheduled' && !r.isScheduled) return false
        if (statusFilter === 'unscheduled' && r.isScheduled) return false
        if (statusFilter === 'paused' && r.status !== 'paused') return false
      }
      if (!searchQuery) return true
      const q = searchQuery.toLowerCase()
      return (
        r.name.toLowerCase().includes(q) ||
        (r.description || '').toLowerCase().includes(q) ||
        (r.source || '').toLowerCase().includes(q)
      )
    })
  }, [unifiedRows, searchQuery, typeFilter, statusFilter])

  // Split rows by sub-tab (pipelines / dbt models / dbt tests)
  const pipelineRows = useMemo(
    () => filteredRows.filter((r) => r.entityType === 'pipeline'),
    [filteredRows],
  )
  const dbtModelRows = useMemo(
    () => filteredRows.filter((r) => r.entityType === 'dbt_run'),
    [filteredRows],
  )
  const dbtTestRows = useMemo(
    () => filteredRows.filter((r) => r.entityType === 'dbt_test'),
    [filteredRows],
  )

  // Schedules tab: every row in our system (pipeline / dbt run / dbt test) that
  // has an active schedule, regardless of the items-tab filters.
  const scheduledRows = useMemo(
    () => unifiedRows.filter((r) => r.isScheduled),
    [unifiedRows],
  )

  const isLoading = jobsLoading || pipelinesLoading

  const refetchAll = () => {
    refetchJobs()
    refetchPipelines()
  }

  // =============================================================================
  // Render
  // =============================================================================
  return (
    <div className="container mx-auto py-6 space-y-6">
      <PageHeader
        icon={<Calendar className="h-5 w-5" />}
        title="Scheduling"
        description="Manage pipelines, jobs, and schedules in one place"
        actions={
          <>
            <InstanceStatus compact />
            <Button
              variant="outline"
              onClick={handleOpenDagsterUI}
              className="border-border/60 bg-background/60 backdrop-blur-sm shadow-sm hover:bg-background hover:shadow-md transition-all"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Dagster UI
            </Button>
            <Button
              asChild
              className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/30 hover:from-indigo-600 hover:to-purple-700 hover:shadow-lg hover:shadow-indigo-500/40 transition-all"
            >
              <Link to="/app/jobs/new">
                <Plus className="mr-2 h-4 w-4" />
                Create Job
              </Link>
            </Button>
          </>
        }
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pipelines</p>
                <p className="text-2xl font-bold">
                  {pipelinesData?.items?.length || 0}
                </p>
              </div>
              <Database className="h-8 w-8 text-muted-foreground opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Jobs</p>
                <p className="text-2xl font-bold">
                  {jobsData?.items?.length || 0}
                </p>
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
                <p className="text-2xl font-bold text-blue-600">
                  {runningCount}
                </p>
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
                <p className="text-2xl font-bold text-yellow-600">
                  {queuedCount}
                </p>
              </div>
              <Activity className="h-8 w-8 text-yellow-500 opacity-50" />
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
                <p className="text-sm text-muted-foreground">Failures</p>
                <p className="text-2xl font-bold text-red-600">
                  {recentFailures}
                </p>
              </div>
              <XCircle className="h-8 w-8 text-red-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="items" className="space-y-4 w-full">
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-4 h-auto gap-1 rounded-xl border border-border/60 bg-gradient-to-br from-muted/40 via-muted/20 to-transparent p-1.5 shadow-sm backdrop-blur-sm">
          <TabsTrigger
            value="items"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <Briefcase className="h-4 w-4" />
            Pipelines &amp; Jobs
          </TabsTrigger>
          <TabsTrigger
            value="assets"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <GitBranch className="h-4 w-4" />
            Assets
          </TabsTrigger>
          <TabsTrigger
            value="schedules"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <Calendar className="h-4 w-4" />
            Schedules
          </TabsTrigger>
          <TabsTrigger
            value="sensors"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <Radio className="h-4 w-4" />
            Sensors
          </TabsTrigger>
        </TabsList>

        {/* Pipelines, dbt models, dbt tests — split sub-tabs */}
        <TabsContent value="items" className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search pipelines or jobs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[170px]">
                <SelectValue placeholder="Schedule" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="scheduled">Scheduled</SelectItem>
                <SelectItem value="unscheduled">Not scheduled</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              size="icon"
              onClick={refetchAll}
              className="hover:bg-indigo-50/60 hover:text-indigo-600 dark:hover:bg-indigo-500/10 transition-all"
              title="Refresh"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <Tabs defaultValue="pipelines" className="space-y-4 w-full">
              <TabsList className="grid w-full grid-cols-3 h-auto gap-1 rounded-xl border border-border/60 bg-muted/30 p-1.5">
                <TabsTrigger
                  value="pipelines"
                  className="group flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-background data-[state=active]:shadow-sm"
                >
                  <GitBranch className="h-4 w-4" />
                  Pipelines
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                    {pipelineRows.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="dbt-models"
                  className="group flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-background data-[state=active]:shadow-sm"
                >
                  <Code2 className="h-4 w-4" />
                  dbt models
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                    {dbtModelRows.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="dbt-tests"
                  className="group flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-background data-[state=active]:shadow-sm"
                >
                  <Code2 className="h-4 w-4" />
                  dbt tests
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                    {dbtTestRows.length}
                  </Badge>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="pipelines">
                {pipelineRows.length > 0 ? (
                  <RowsTable
                    rows={pipelineRows}
                    onTrigger={(jobId) => triggerMutation.mutate(jobId)}
                    onTogglePause={handleTogglePause}
                    onDeleteJob={(j) => setDeleteTarget(j)}
                    triggerPending={triggerMutation.isPending}
                  />
                ) : (
                  <EmptyState
                    title="No pipelines yet"
                    description="Create a dlt pipeline to ingest data into the lake."
                    primary={{
                      label: 'New Pipeline',
                      to: '/app/pipelines/new',
                    }}
                  />
                )}
              </TabsContent>

              <TabsContent value="dbt-models">
                {dbtModelRows.length > 0 ? (
                  <RowsTable
                    rows={dbtModelRows}
                    onTrigger={(jobId) => triggerMutation.mutate(jobId)}
                    onTogglePause={handleTogglePause}
                    onDeleteJob={(j) => setDeleteTarget(j)}
                    triggerPending={triggerMutation.isPending}
                  />
                ) : (
                  <EmptyState
                    title="No scheduled dbt model runs"
                    description="Schedule a dbt run job to materialize your models on a cadence."
                    primary={{
                      label: 'Schedule dbt run',
                      to: '/app/jobs/new?kind=dbt_run',
                    }}
                  />
                )}
              </TabsContent>

              <TabsContent value="dbt-tests">
                {dbtTestRows.length > 0 ? (
                  <RowsTable
                    rows={dbtTestRows}
                    onTrigger={(jobId) => triggerMutation.mutate(jobId)}
                    onTogglePause={handleTogglePause}
                    onDeleteJob={(j) => setDeleteTarget(j)}
                    triggerPending={triggerMutation.isPending}
                  />
                ) : (
                  <EmptyState
                    title="No scheduled dbt tests"
                    description="Schedule dbt tests to validate your models on a cadence."
                    primary={{
                      label: 'Schedule dbt test',
                      to: '/app/jobs/new?kind=dbt_test',
                    }}
                  />
                )}
              </TabsContent>
            </Tabs>
          )}
        </TabsContent>

        <TabsContent value="assets">
          <AssetGraph
            onAssetSelect={setSelectedAssetKey}
            selectedAssetKey={selectedAssetKey}
            className="min-h-[600px]"
          />
        </TabsContent>

        <TabsContent value="schedules">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : scheduledRows.length > 0 ? (
            <RowsTable
              rows={scheduledRows}
              onTrigger={(jobId) => triggerMutation.mutate(jobId)}
              onTogglePause={handleTogglePause}
              onDeleteJob={(j) => setDeleteTarget(j)}
              triggerPending={triggerMutation.isPending}
            />
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">
                  No schedules configured
                </h3>
                <p className="text-muted-foreground text-center mb-4">
                  Configure a schedule on any pipeline, dbt model, or dbt test
                  to see it here.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  <Button
                    asChild
                    className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/30 hover:from-indigo-600 hover:to-purple-700 hover:shadow-lg hover:shadow-indigo-500/40 transition-all"
                  >
                    <Link to="/app/pipelines/new">
                      <Plus className="mr-2 h-4 w-4" />
                      New Pipeline
                    </Link>
                  </Button>
                  <Button
                    asChild
                    variant="outline"
                    className="border-border/60 hover:border-indigo-400/60 hover:text-indigo-600 hover:bg-indigo-50/40 dark:hover:bg-indigo-500/10 transition-all"
                  >
                    <Link to="/app/jobs/new?kind=dbt_run">
                      <Plus className="mr-2 h-4 w-4" />
                      Schedule dbt run
                    </Link>
                  </Button>
                  <Button
                    asChild
                    variant="outline"
                    className="border-border/60 hover:border-indigo-400/60 hover:text-indigo-600 hover:bg-indigo-50/40 dark:hover:bg-indigo-500/10 transition-all"
                  >
                    <Link to="/app/jobs/new?kind=dbt_test">
                      <Plus className="mr-2 h-4 w-4" />
                      Schedule dbt test
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="sensors">
          <SensorList />
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation */}
      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Schedule</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove the schedule for "
              {deleteTarget?.dag_id}"? This will detach the job and stop
              automatic runs. The underlying pipeline (if any) will be kept.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-gradient-to-br from-red-500 to-rose-600 text-white shadow-md shadow-red-500/30 hover:from-red-600 hover:to-rose-700 hover:shadow-lg hover:shadow-red-500/40 transition-all"
              onClick={() =>
                deleteTarget && deleteMutation.mutate(deleteTarget.id)
              }
            >
              {deleteMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// =============================================================================
// UnifiedRowItem
// =============================================================================
interface UnifiedRowItemProps {
  row: UnifiedRow
  onTrigger: (jobId: string) => void
  onTogglePause: (job: Job) => void
  onDeleteJob: (job: Job) => void
  triggerPending: boolean
}

function UnifiedRowItem({
  row,
  onTrigger,
  onTogglePause,
  onDeleteJob,
  triggerPending,
}: UnifiedRowItemProps) {
  const { job, pipeline, entityType } = row

  return (
    <TableRow className="hover:bg-muted/30">
      <TableCell className="font-medium">
        <div className="flex flex-col">
          <span className="truncate max-w-[260px]" title={row.name}>
            {row.name}
          </span>
          {row.description && (
            <span
              className="text-xs text-muted-foreground line-clamp-1 max-w-[260px]"
              title={row.description}
            >
              {row.description}
            </span>
          )}
        </div>
      </TableCell>
      <TableCell>
        {entityType === 'pipeline' ? (
          <Badge variant="outline" className="border-purple-400 text-purple-600">
            <GitBranch className="mr-1 h-3 w-3" />
            Pipeline
          </Badge>
        ) : entityType === 'dbt_test' ? (
          <Badge variant="outline" className="border-pink-400 text-pink-600">
            <Code2 className="mr-1 h-3 w-3" />
            dbt test
          </Badge>
        ) : (
          <Badge variant="outline" className="border-blue-400 text-blue-600">
            <Code2 className="mr-1 h-3 w-3" />
            dbt run
          </Badge>
        )}
      </TableCell>
      <TableCell>
        <span
          className="font-mono text-xs truncate inline-block max-w-[200px] align-middle"
          title={row.source || '—'}
        >
          {row.source || '—'}
        </span>
      </TableCell>
      <TableCell>
        <span className="flex items-center gap-1.5 text-sm">
          {row.isScheduled ? (
            <Calendar className="h-3.5 w-3.5 text-green-600" />
          ) : (
            <CalendarOff className="h-3.5 w-3.5 text-muted-foreground" />
          )}
          <span className="font-medium">{row.scheduleLabel}</span>
        </span>
      </TableCell>
      <TableCell>
        {row.status === 'no-schedule' ? (
          <Badge variant="outline" className="text-muted-foreground">
            <CalendarOff className="mr-1 h-3 w-3" />
            Not scheduled
          </Badge>
        ) : (
          <Badge variant="outline" className={getStatusClasses(row.status)}>
            {row.status}
          </Badge>
        )}
      </TableCell>
      <TableCell>
        {row.lastRun ? (
          <div className="flex flex-col text-xs">
            <Badge
              variant={
                row.lastRun.status === 'SUCCESS' ||
                row.lastRun.status === 'success'
                  ? 'default'
                  : row.lastRun.status === 'FAILURE' ||
                    row.lastRun.status === 'failed'
                  ? 'destructive'
                  : 'secondary'
              }
              className="text-xs w-fit"
            >
              {row.lastRun.status}
            </Badge>
            {row.lastRun.at && (
              <span className="text-muted-foreground mt-0.5">
                {formatDistanceToNow(new Date(row.lastRun.at))} ago
              </span>
            )}
          </div>
        ) : (
          <span className="text-muted-foreground text-xs">Never</span>
        )}
      </TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1">
          {!job ? (
            <Button
              size="sm"
              asChild
              className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-sm shadow-indigo-500/25 hover:from-indigo-600 hover:to-purple-700 hover:shadow-md hover:shadow-indigo-500/40 transition-all"
            >
              <Link
                to={
                  pipeline
                    ? `/app/jobs/new?pipeline_id=${pipeline.id}`
                    : '/app/jobs/new'
                }
              >
                <Calendar className="mr-1 h-3 w-3" />
                Configure
              </Link>
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                onClick={() => onTrigger(job.id)}
                disabled={triggerPending || job.status === 'archived'}
                className="bg-gradient-to-br from-emerald-500 to-green-600 text-white shadow-sm shadow-emerald-500/25 hover:from-emerald-600 hover:to-green-700 hover:shadow-md hover:shadow-emerald-500/40 disabled:opacity-50 disabled:hover:shadow-sm transition-all"
              >
                {triggerPending ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : (
                  <Play className="mr-1 h-3 w-3 fill-current" />
                )}
                Run
              </Button>
              <Button
                variant="outline"
                size="sm"
                asChild
                className="border-border/60 bg-background/60 hover:bg-background hover:border-indigo-400/60 hover:text-indigo-600 transition-all"
              >
                <Link to={`/app/jobs/${job.id}/edit`}>
                  <Settings className="mr-1 h-3 w-3" />
                  Schedule
                </Link>
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="hover:bg-muted/60 transition-colors"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem asChild>
                    <Link to={`/app/jobs/${job.id}`}>
                      <Eye className="mr-2 h-4 w-4" />
                      View Details
                    </Link>
                  </DropdownMenuItem>
                  {pipeline && (
                    <DropdownMenuItem asChild>
                      <Link to={`/app/pipelines/${pipeline.id}/edit`}>
                        <Database className="mr-2 h-4 w-4" />
                        Edit Pipeline
                      </Link>
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  {job.status === 'active' ? (
                    <DropdownMenuItem onClick={() => onTogglePause(job)}>
                      <Pause className="mr-2 h-4 w-4" />
                      Pause
                    </DropdownMenuItem>
                  ) : job.status === 'paused' ? (
                    <DropdownMenuItem onClick={() => onTogglePause(job)}>
                      <Play className="mr-2 h-4 w-4" />
                      Resume
                    </DropdownMenuItem>
                  ) : null}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => onDeleteJob(job)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Remove Schedule
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}
        </div>
      </TableCell>
    </TableRow>
  )
}

// =============================================================================
// RowsTable — shared table wrapper used by each sub-tab
// =============================================================================
interface RowsTableProps {
  rows: UnifiedRow[]
  onTrigger: (jobId: string) => void
  onTogglePause: (job: Job) => void
  onDeleteJob: (job: Job) => void
  triggerPending: boolean
}

function RowsTable({
  rows,
  onTrigger,
  onTogglePause,
  onDeleteJob,
  triggerPending,
}: RowsTableProps) {
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Schedule</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last Run</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <UnifiedRowItem
                key={`${row.entityType}-${row.id}`}
                row={row}
                onTrigger={onTrigger}
                onTogglePause={onTogglePause}
                onDeleteJob={onDeleteJob}
                triggerPending={triggerPending}
              />
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// EmptyState — shown when a sub-tab has no rows
// =============================================================================
interface EmptyStateProps {
  title: string
  description: string
  primary: { label: string; to: string }
}

function EmptyState({ title, description, primary }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <Database className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">{title}</h3>
        <p className="text-muted-foreground text-center mb-4">{description}</p>
        <Button
          asChild
          className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/30 hover:from-indigo-600 hover:to-purple-700 hover:shadow-lg hover:shadow-indigo-500/40 transition-all"
        >
          <Link to={primary.to}>
            <Plus className="mr-2 h-4 w-4" />
            {primary.label}
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

export default SchedulingPage
