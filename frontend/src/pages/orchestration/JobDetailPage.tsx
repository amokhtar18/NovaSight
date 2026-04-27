/**
 * NovaSight Job Detail Page
 * ==========================
 *
 * Displays details for a specific Dagster job, including:
 * - Job configuration overview
 * - Run history
 * - Run logs
 */

import { useState } from 'react'
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobService, Job } from '@/services/jobService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { PageHeader } from '@/components/common'
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
  ArrowLeft,
  Play,
  Pause,
  Settings,
  Loader2,
  Trash2,
  RefreshCw,
  Zap,
  GitBranch,
  Code2,
  Clock,
  Activity,
  ExternalLink,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from '@/components/ui/use-toast'
import { getStatusClasses } from '@/lib/colors'

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [showDelete, setShowDelete] = useState(false)
  const [activeTab, setActiveTab] = useState(location.pathname.endsWith('/runs') ? 'runs' : 'overview')

  // Fetch job details
  const {
    data: job,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobService.get(jobId!),
    enabled: !!jobId,
  })

  // Fetch run history
  const {
    data: runsData,
    isLoading: runsLoading,
    refetch: refetchRuns,
  } = useQuery({
    queryKey: ['job-runs', jobId],
    queryFn: () => jobService.listRuns(jobId!, { per_page: 50 }),
    enabled: !!jobId,
    refetchInterval: 15000,
  })

  // Mutations
  const triggerMutation = useMutation({
    mutationFn: () => jobService.trigger(jobId!),
    onSuccess: (result) => {
      if (result.success) {
        toast({ title: 'Job Triggered', description: `Run started: ${result.run_id}` })
        queryClient.invalidateQueries({ queryKey: ['job-runs', jobId] })
      } else {
        toast({ title: 'Trigger Failed', description: result.error || 'Unknown error', variant: 'destructive' })
      }
    },
    onError: (err: unknown) => {
      let message = 'Failed to trigger job'
      if (err && typeof err === 'object') {
        const axiosErr = err as { response?: { data?: { error?: { message?: string } } }; message?: string }
        if (axiosErr.response?.data?.error?.message) {
          message = axiosErr.response.data.error.message
        } else if (axiosErr.message) {
          message = axiosErr.message
        }
      }
      toast({ title: 'Error', description: message, variant: 'destructive' })
    },
  })

  const pauseMutation = useMutation({
    mutationFn: () => jobService.pause(jobId!),
    onSuccess: () => {
      toast({ title: 'Job Paused' })
      queryClient.invalidateQueries({ queryKey: ['job', jobId] })
    },
  })

  const resumeMutation = useMutation({
    mutationFn: () => jobService.resume(jobId!),
    onSuccess: () => {
      toast({ title: 'Job Resumed' })
      queryClient.invalidateQueries({ queryKey: ['job', jobId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => jobService.delete(jobId!),
    onSuccess: () => {
      toast({ title: 'Job Deleted' })
      navigate('/app/jobs')
    },
  })

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      draft: 'outline',
      active: 'default',
      paused: 'secondary',
      archived: 'destructive',
    }
    const variant = variants[status] || 'outline'
    return <Badge variant={variant} className={getStatusClasses(status)}>{status}</Badge>
  }

  const getRunStatusBadge = (status: string) => {
    return <Badge variant="outline" className={getStatusClasses(status)}>{status}</Badge>
  }

  const getRunStatusIcon = (status: string) => {
    switch (status) {
      case 'SUCCESS': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'FAILURE': return <XCircle className="h-4 w-4 text-red-500" />
      case 'STARTED': return <Activity className="h-4 w-4 text-blue-500 animate-pulse" />
      case 'QUEUED': return <Clock className="h-4 w-4 text-yellow-500" />
      default: return <AlertTriangle className="h-4 w-4 text-gray-400" />
    }
  }

  const getScheduleDisplay = (job: Job) => {
    if (job.schedule_type === 'manual') return 'Manual'
    if (job.schedule_type === 'preset') {
      const preset = job.schedule_preset?.replace('@', '') || ''
      return preset ? preset.charAt(0).toUpperCase() + preset.slice(1) : 'Preset'
    }
    return job.schedule_cron || 'Custom'
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex flex-col items-center justify-center gap-4 py-12">
          <AlertTriangle className="h-12 w-12 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Job Not Found</h2>
          <p className="text-muted-foreground">
            The requested job could not be found or you don&apos;t have access to it.
          </p>
          <Button asChild>
            <Link to="/app/jobs">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Jobs
            </Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <PageHeader
        icon={<GitBranch className="h-5 w-5" />}
        title={job.dag_id}
        description={job.description || 'No description'}
        eyebrow={
          <div className="flex items-center gap-2">
            <Link
              to="/app/jobs"
              className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-3 w-3" />
              Jobs
            </Link>
            {job.type === 'pipeline' ? (
              <Badge variant="outline" className="border-purple-400 text-purple-600">
                <GitBranch className="mr-1 h-3 w-3" /> Pipeline
              </Badge>
            ) : job.type === 'dbt' ? (
              <Badge variant="outline" className="border-blue-400 text-blue-600">
                <Code2 className="mr-1 h-3 w-3" /> dbt
              </Badge>
            ) : (
              <Badge variant="outline" className="border-orange-400 text-orange-600">
                <Zap className="mr-1 h-3 w-3" /> dlt
              </Badge>
            )}
            {getStatusBadge(job.status)}
          </div>
        }
        actions={
          <>
            <Button
              onClick={() => triggerMutation.mutate()}
              disabled={triggerMutation.isPending || job.status === 'archived'}
            >
              {triggerMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Run Now
            </Button>
            {job.status === 'active' && (
              <Button variant="outline" onClick={() => pauseMutation.mutate()}>
                <Pause className="mr-2 h-4 w-4" /> Pause
              </Button>
            )}
            {job.status === 'paused' && (
              <Button variant="outline" onClick={() => resumeMutation.mutate()}>
                <Play className="mr-2 h-4 w-4" /> Resume
              </Button>
            )}
            <Button variant="outline" asChild>
              <Link to={`/app/jobs/${jobId}/edit`}>
                <Settings className="mr-2 h-4 w-4" /> Edit
              </Link>
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setShowDelete(true)}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </>
        }
      />

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="runs">
            Runs
            {runsData?.total ? (
              <Badge variant="secondary" className="ml-2 text-xs">{runsData.total}</Badge>
            ) : null}
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Schedule</span>
                  <span className="font-medium">{getScheduleDisplay(job)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Timezone</span>
                  <span className="font-medium">{job.timezone}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created</span>
                  <span className="font-medium text-sm">
                    {formatDistanceToNow(new Date(job.created_at))} ago
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Updated</span>
                  <span className="font-medium text-sm">
                    {formatDistanceToNow(new Date(job.updated_at))} ago
                  </span>
                </div>
                {job.deployed_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Deployed</span>
                    <span className="font-medium text-sm">
                      {formatDistanceToNow(new Date(job.deployed_at))} ago
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Last Run</CardTitle>
              </CardHeader>
              <CardContent>
                {job.last_run ? (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Status</span>
                      {getRunStatusBadge(job.last_run.status)}
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Run ID</span>
                      <code className="text-xs bg-muted px-2 py-0.5 rounded">
                        {job.last_run.run_id?.substring(0, 8)}
                      </code>
                    </div>
                    {job.last_run.start_time && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Started</span>
                        <span className="text-sm">
                          {new Date(job.last_run.start_time).toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">No runs yet</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Tags */}
          {job.tags && job.tags.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Tags</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {job.tags.map((tag, idx) => (
                    <Badge key={idx} variant="secondary">{tag}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Runs Tab */}
        <TabsContent value="runs" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">Run History</h3>
            <Button variant="ghost" size="icon" onClick={() => refetchRuns()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {runsLoading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : (runsData?.items?.length || 0) > 0 ? (
            <ScrollArea className="h-[500px]">
              <div className="space-y-2">
                {(runsData?.items || []).map((run) => (
                  <Card key={run.run_id} className="hover:shadow-sm transition-shadow">
                    <CardContent className="py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {getRunStatusIcon(run.status)}
                        <div>
                          <code className="text-sm bg-muted px-2 py-0.5 rounded">
                            {run.run_id?.substring(0, 8)}
                          </code>
                          <span className="ml-2">{getRunStatusBadge(run.status)}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {run.start_time && (
                          <span>{new Date(run.start_time).toLocaleString()}</span>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => window.open(`http://localhost:3000/runs/${run.run_id}`, '_blank')}
                        >
                          <ExternalLink className="h-3 w-3 mr-1" />
                          Dagster
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Activity className="h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-muted-foreground">No runs recorded yet</p>
                <Button className="mt-4" onClick={() => triggerMutation.mutate()}>
                  <Play className="mr-2 h-4 w-4" /> Run Now
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation */}
      <AlertDialog open={showDelete} onOpenChange={setShowDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Job</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{job.dag_id}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteMutation.mutate()}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default JobDetailPage
