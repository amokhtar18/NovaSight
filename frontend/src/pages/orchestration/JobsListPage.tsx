/**
 * NovaSight Jobs List Page
 * =========================
 *
 * Unified page for managing Dagster jobs that execute PySpark apps
 * on remote Spark clusters. Replaces separate DAGs and PySpark
 * orchestration pages.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobService, Job } from '@/services/jobService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
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
  Zap,
  GitBranch,
  Search,
  RefreshCw,
  ArrowRight,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { toast } from '@/components/ui/use-toast'
import { getStatusClasses } from '@/lib/colors'

export function JobsListPage() {
  const queryClient = useQueryClient()
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch jobs
  const {
    data: jobsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['jobs', statusFilter, typeFilter],
    queryFn: () =>
      jobService.list({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type: typeFilter !== 'all' ? (typeFilter as 'spark' | 'pipeline') : undefined,
        per_page: 50,
      }),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

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
    onError: (err: Error) => {
      toast({
        title: 'Error',
        description: err.message,
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

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-destructive">Failed to load jobs</p>
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Spark Jobs</h1>
          <p className="text-muted-foreground">
            Manage PySpark jobs running on remote Spark clusters
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link to="/app/jobs/new">
              <Plus className="mr-2 h-4 w-4" />
              Create Job
            </Link>
          </Button>
        </div>
      </div>

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
        <Button variant="ghost" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Jobs Grid */}
      {filteredJobs.length > 0 ? (
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
    </div>
  )
}

export default JobsListPage
