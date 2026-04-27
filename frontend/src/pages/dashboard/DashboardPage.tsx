/**
 * DashboardPage — primary landing view for authenticated users.
 *
 * Sections (top → bottom):
 * 1. PageHeader with "Ask AI" entry.
 * 2. Live summary metric cards (connections, active pipelines, charts,
 *    dashboards) driven from real backend services.
 * 3. Quickstart smart-art — a 6-step guided onboarding stepper that
 *    visualises the end-to-end NovaSight workflow and lights up each step
 *    once the tenant has at least one matching artefact.
 * 4. Latest job runs (derived from each job's `last_run` field) +
 *    favourite/pinned dashboards (localStorage backed).
 *
 * Status colours (success / warning / danger) are reserved for state
 * indicators only.
 */

import * as React from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Database,
  GitBranch,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  TrendingUp,
  Sparkles,
  ArrowRight,
  LayoutDashboard,
  Star,
  Plug,
  Workflow,
  Calendar,
  PieChart,
  Check,
  CircleDot,
  Plus,
} from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { DashboardWidget } from '@/components/dashboard/DashboardWidget'
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from '@/components/ui/glass-card'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/common'
import { GridBackground } from '@/components/backgrounds/GridBackground'
import { fadeVariants, staggerContainerVariants } from '@/lib/motion-variants'
import { cn } from '@/lib/utils'

import { dataSourceService } from '@/services/dataSourceService'
import { pipelineService } from '@/services/pipelineService'
import { jobService, type Job } from '@/services/jobService'
import { chartService } from '@/services/chartService'
import { useDashboards } from '@/features/dashboards/hooks/useDashboards'
import { useFavoriteDashboards } from '@/features/dashboards/hooks/useFavoriteDashboards'
import type { Dashboard } from '@/types/dashboard'

// =============================================================================
// Run status helper
// =============================================================================

type NormalisedRunStatus = 'success' | 'running' | 'failed' | 'queued'

function normaliseRunStatus(status: string | undefined): NormalisedRunStatus {
  const s = (status ?? '').toUpperCase()
  if (s === 'SUCCESS') return 'success'
  if (s === 'FAILURE' || s === 'CANCELED') return 'failed'
  if (s === 'STARTED' || s === 'STARTING' || s === 'RUNNING') return 'running'
  return 'queued'
}

function RunStatusIcon({ status }: { status: NormalisedRunStatus }): React.ReactElement | null {
  switch (status) {
    case 'success':
      return <CheckCircle className="h-4 w-4 text-success" aria-label="Succeeded" />
    case 'running':
      return <Clock className="h-4 w-4 animate-pulse text-info" aria-label="Running" />
    case 'failed':
      return <AlertTriangle className="h-4 w-4 text-danger" aria-label="Failed" />
    case 'queued':
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" aria-label="Queued" />
  }
}

function formatRelative(timestamp: string | undefined): string {
  if (!timestamp) return '—'
  const d = new Date(timestamp)
  if (Number.isNaN(d.getTime())) return '—'
  const diffMs = Date.now() - d.getTime()
  if (diffMs < 0) return d.toLocaleString()
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString()
}

function formatDuration(start: string | undefined, end: string | undefined): string {
  if (!start || !end) return ''
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (!Number.isFinite(ms) || ms < 0) return ''
  const totalSec = Math.round(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

// =============================================================================
// Quickstart smart-art
// =============================================================================

interface QuickstartStep {
  readonly id: string
  readonly title: string
  readonly description: string
  readonly icon: React.ComponentType<{ className?: string }>
  readonly to: string
  readonly completed: boolean
}

interface QuickstartCounts {
  readonly connections: number
  readonly pipelines: number
  readonly schedules: number
  readonly charts: number
  readonly dashboards: number
}

function buildQuickstartSteps(counts: QuickstartCounts): QuickstartStep[] {
  return [
    {
      id: 'connect',
      title: 'Connect a source',
      description: 'Add a database or upload a file.',
      icon: Plug,
      to: '/app/datasources',
      completed: counts.connections > 0,
    },
    {
      id: 'pipeline',
      title: 'Build a pipeline',
      description: 'Move data into the lake with dlt.',
      icon: Workflow,
      to: '/app/pipelines',
      completed: counts.pipelines > 0,
    },
    {
      id: 'schedule',
      title: 'Schedule a job',
      description: 'Run pipelines on a cadence.',
      icon: Calendar,
      to: '/app/jobs',
      completed: counts.schedules > 0,
    },
    {
      id: 'transform',
      title: 'Model with dbt',
      description: 'Transform data into marts.',
      icon: GitBranch,
      to: '/app/dbt',
      completed: false,
    },
    {
      id: 'chart',
      title: 'Create a chart',
      description: 'Visualise a query result.',
      icon: PieChart,
      to: '/app/charts',
      completed: counts.charts > 0,
    },
    {
      id: 'dashboard',
      title: 'Build a dashboard',
      description: 'Compose charts into a dashboard.',
      icon: LayoutDashboard,
      to: '/app/dashboards',
      completed: counts.dashboards > 0,
    },
  ]
}

function QuickstartSmartArt({ counts }: { counts: QuickstartCounts }): React.ReactElement {
  const steps = buildQuickstartSteps(counts)
  const completedCount = steps.filter((s) => s.completed).length
  const progressPct = Math.round((completedCount / steps.length) * 100)

  return (
    <GlassCard variant="elevated">
      <GlassCardHeader>
        <div className="flex items-center justify-between gap-4">
          <div>
            <GlassCardTitle className="text-base">Quickstart</GlassCardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              The end-to-end path from raw data to a published dashboard.
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Progress</p>
            <p className="text-sm font-semibold text-foreground">
              {completedCount} / {steps.length}
            </p>
          </div>
        </div>
      </GlassCardHeader>
      <GlassCardContent>
        <div
          className="mb-6 h-1.5 w-full overflow-hidden rounded-full bg-bg-tertiary"
          role="progressbar"
          aria-valuenow={progressPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Quickstart progress"
        >
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        <ol className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          {steps.map((step, index) => {
            const Icon = step.icon
            const isLast = index === steps.length - 1
            return (
              <li key={step.id} className="relative">
                {!isLast && (
                  <ArrowRight
                    className="pointer-events-none absolute right-[-14px] top-6 hidden h-4 w-4 text-muted-foreground/40 lg:block"
                    aria-hidden
                  />
                )}
                <Link
                  to={step.to}
                  className={cn(
                    'group flex h-full flex-col rounded-lg border p-3 transition-colors',
                    step.completed
                      ? 'border-success/40 bg-success/5 hover:bg-success/10'
                      : 'border-border bg-card/40 hover:bg-bg-tertiary/60',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold',
                        step.completed
                          ? 'border-success/40 bg-success/15 text-success'
                          : 'border-border bg-bg-tertiary text-muted-foreground',
                      )}
                      aria-hidden
                    >
                      {step.completed ? <Check className="h-4 w-4" /> : index + 1}
                    </span>
                    <Icon
                      className={cn(
                        'h-4 w-4',
                        step.completed ? 'text-success' : 'text-muted-foreground',
                      )}
                      aria-hidden
                    />
                  </div>
                  <p className="mt-3 text-sm font-medium text-foreground">{step.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{step.description}</p>
                  <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                    Open <ArrowRight className="h-3 w-3" />
                  </span>
                </Link>
              </li>
            )
          })}
        </ol>
      </GlassCardContent>
    </GlassCard>
  )
}

// =============================================================================
// Page
// =============================================================================

export function DashboardPage(): React.ReactElement {
  const { user } = useAuth()

  const connectionsQuery = useQuery({
    queryKey: ['home', 'connections', 'count'],
    queryFn: () => dataSourceService.getAll({ per_page: 1 }),
    staleTime: 30_000,
  })

  const allPipelinesQuery = useQuery({
    queryKey: ['home', 'pipelines', 'count'],
    queryFn: () => pipelineService.list({ per_page: 1 }),
    staleTime: 30_000,
  })

  const activePipelinesQuery = useQuery({
    queryKey: ['home', 'pipelines', 'active', 'count'],
    queryFn: () => pipelineService.list({ status: 'active', per_page: 1 }),
    staleTime: 30_000,
  })

  const chartsQuery = useQuery({
    queryKey: ['home', 'charts', 'count'],
    queryFn: () => chartService.list({ per_page: 1 }),
    staleTime: 30_000,
  })

  const dashboardsQuery = useDashboards()

  const jobsQuery = useQuery({
    queryKey: ['home', 'jobs', 'recent'],
    queryFn: () => jobService.list({ per_page: 50 }),
    staleTime: 15_000,
    retry: false,
  })

  const connectionsCount = connectionsQuery.data?.total ?? 0
  const totalPipelines = allPipelinesQuery.data?.total ?? 0
  const activePipelines = activePipelinesQuery.data?.total ?? 0
  const chartsCount = chartsQuery.data?.total ?? 0
  const dashboardsList: Dashboard[] = Array.isArray(dashboardsQuery.data)
    ? dashboardsQuery.data
    : []
  const dashboardsCount = dashboardsList.length

  const recentJobs: Job[] = React.useMemo(() => {
    const jobs = jobsQuery.data?.items ?? []
    const withRuns = jobs.filter((j) => j.last_run?.start_time)
    return [...withRuns]
      .sort((a, b) => {
        const ta = new Date(a.last_run?.start_time ?? 0).getTime()
        const tb = new Date(b.last_run?.start_time ?? 0).getTime()
        return tb - ta
      })
      .slice(0, 5)
  }, [jobsQuery.data])

  const scheduledJobs = (jobsQuery.data?.items ?? []).filter(
    (j) => j.schedule_type !== 'manual',
  ).length

  const stats = [
    {
      label: 'Data Connections',
      value: connectionsCount,
      icon: Database,
      iconColor: 'indigo' as const,
      to: '/app/datasources',
    },
    {
      label: 'Active Pipelines',
      value: activePipelines,
      subtitle: totalPipelines > 0 ? `of ${totalPipelines} total` : undefined,
      icon: GitBranch,
      iconColor: 'green' as const,
      to: '/app/pipelines',
    },
    {
      label: 'Charts',
      value: chartsCount,
      icon: BarChart3,
      iconColor: 'purple' as const,
      to: '/app/charts',
    },
    {
      label: 'Dashboards',
      value: dashboardsCount,
      icon: LayoutDashboard,
      iconColor: 'pink' as const,
      to: '/app/dashboards',
    },
  ]

  const { favorites, removeFavorite } = useFavoriteDashboards()
  const favoriteDashboards: Dashboard[] = React.useMemo(() => {
    if (favorites.length === 0) return []
    const byId = new Map(dashboardsList.map((d) => [d.id, d]))
    return favorites
      .map((id) => byId.get(id))
      .filter((d): d is Dashboard => Boolean(d))
  }, [favorites, dashboardsList])

  React.useEffect(() => {
    if (dashboardsQuery.isLoading || favorites.length === 0) return
    const ids = new Set(dashboardsList.map((d) => d.id))
    favorites.forEach((id) => {
      if (!ids.has(id)) removeFavorite(id)
    })
  }, [dashboardsQuery.isLoading, dashboardsList, favorites, removeFavorite])

  return (
    <div className="relative min-h-full">
      <GridBackground showOrbs gridOpacity={0.02} />

      <motion.div
        variants={staggerContainerVariants}
        initial="hidden"
        animate="visible"
        className="relative space-y-8"
      >
        <motion.div variants={fadeVariants}>
          <PageHeader
            title="Dashboard"
            description={
              user?.name
                ? `Welcome back, ${user.name}. Here's what's happening with your data platform.`
                : "Here's what's happening with your data platform."
            }
            actions={
              <Button variant="ai" asChild className="hidden sm:inline-flex">
                <Link to="/app/query">
                  <Sparkles className="mr-2 h-4 w-4" />
                  Ask AI
                </Link>
              </Button>
            }
          />
        </motion.div>

        <motion.div variants={fadeVariants}>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <Link
                key={stat.label}
                to={stat.to}
                className="block rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                aria-label={`${stat.label}: ${stat.value}`}
              >
                <MetricCard
                  label={stat.label}
                  value={stat.value}
                  subtitle={stat.subtitle}
                  icon={stat.icon}
                  iconColor={stat.iconColor}
                  animated
                />
              </Link>
            ))}
          </div>
        </motion.div>

        <motion.div variants={fadeVariants}>
          <QuickstartSmartArt
            counts={{
              connections: connectionsCount,
              pipelines: totalPipelines,
              schedules: scheduledJobs,
              charts: chartsCount,
              dashboards: dashboardsCount,
            }}
          />
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-3">
          <motion.div variants={fadeVariants} className="lg:col-span-2">
            <DashboardWidget
              title="Latest Job Runs"
              subtitle="Most recent execution per scheduled job"
              icon={<Activity className="h-4 w-4" />}
              onRefresh={() => {
                void jobsQuery.refetch()
              }}
            >
              {jobsQuery.isLoading ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  Loading runs…
                </p>
              ) : jobsQuery.isError ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  Could not load job runs.
                </p>
              ) : recentJobs.length === 0 ? (
                <div className="flex flex-col items-center gap-3 py-8 text-center">
                  <CircleDot className="h-6 w-6 text-muted-foreground" aria-hidden />
                  <p className="text-sm text-muted-foreground">
                    No job runs yet. Schedule a pipeline to get started.
                  </p>
                  <Button variant="outline" size="sm" asChild>
                    <Link to="/app/jobs/new">
                      <Plus className="mr-2 h-4 w-4" /> Create Job
                    </Link>
                  </Button>
                </div>
              ) : (
                <ul className="space-y-2">
                  {recentJobs.map((job, index) => {
                    const status = normaliseRunStatus(job.last_run?.status)
                    const duration = formatDuration(
                      job.last_run?.start_time,
                      job.last_run?.end_time,
                    )
                    return (
                      <motion.li
                        key={job.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className={cn(
                          'flex items-center justify-between rounded-lg border border-border bg-card/40 p-3',
                          'transition-colors hover:bg-bg-tertiary/60',
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <RunStatusIcon status={status} />
                          <div>
                            <p className="font-medium text-foreground">{job.job_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {job.type.toUpperCase()}
                              {duration ? ` · ${duration}` : ''}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-muted-foreground">
                            {formatRelative(job.last_run?.end_time ?? job.last_run?.start_time)}
                          </p>
                          <Button
                            variant="link"
                            size="sm"
                            className="h-auto p-0 text-xs"
                            asChild
                          >
                            <Link to={`/app/jobs/${job.id}`}>
                              View Details <ArrowRight className="ml-1 h-3 w-3" />
                            </Link>
                          </Button>
                        </div>
                      </motion.li>
                    )
                  })}
                </ul>
              )}
            </DashboardWidget>
          </motion.div>

          <motion.div variants={fadeVariants} className="space-y-6">
            <GlassCard variant="elevated">
              <GlassCardHeader>
                <div className="flex items-center justify-between">
                  <GlassCardTitle className="text-base">Favorite Dashboards</GlassCardTitle>
                  <Button variant="link" size="sm" className="h-auto p-0 text-xs" asChild>
                    <Link to="/app/dashboards">
                      All <ArrowRight className="ml-1 h-3 w-3" />
                    </Link>
                  </Button>
                </div>
              </GlassCardHeader>
              <GlassCardContent>
                {favoriteDashboards.length > 0 ? (
                  <ul className="space-y-2">
                    {favoriteDashboards.map((d) => (
                      <li key={d.id}>
                        <Link
                          to={`/app/dashboards/${d.id}`}
                          className="flex items-center justify-between rounded-lg border border-border bg-card/40 p-3 transition-colors hover:bg-bg-tertiary/60"
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <Star
                              className="h-4 w-4 shrink-0 fill-yellow-400 text-yellow-400"
                              aria-hidden
                            />
                            <span className="truncate text-sm font-medium text-foreground">
                              {d.name}
                            </span>
                          </div>
                          <ArrowRight className="h-3 w-3 text-muted-foreground" aria-hidden />
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="flex flex-col items-center gap-2 py-4 text-center">
                    <Star className="h-5 w-5 text-muted-foreground" aria-hidden />
                    <p className="text-xs text-muted-foreground">
                      Star a dashboard from the Dashboards page to pin it here.
                    </p>
                  </div>
                )}
              </GlassCardContent>
            </GlassCard>

            <GlassCard>
              <GlassCardHeader>
                <GlassCardTitle className="text-base">Quick Actions</GlassCardTitle>
              </GlassCardHeader>
              <GlassCardContent className="space-y-2">
                <Button asChild className="w-full justify-start">
                  <Link to="/app/datasources">
                    <Database className="mr-2 h-4 w-4" />
                    New Connection
                  </Link>
                </Button>
                <Button variant="outline" asChild className="w-full justify-start">
                  <Link to="/app/pipelines/new">
                    <Workflow className="mr-2 h-4 w-4" />
                    Create Pipeline
                  </Link>
                </Button>
                <Button variant="outline" asChild className="w-full justify-start">
                  <Link to="/app/dashboards">
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Build Dashboard
                  </Link>
                </Button>
                <Button variant="outline" asChild className="w-full justify-start">
                  <Link to="/app/query">
                    <TrendingUp className="mr-2 h-4 w-4" />
                    Run Analysis
                  </Link>
                </Button>
              </GlassCardContent>
            </GlassCard>
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}
