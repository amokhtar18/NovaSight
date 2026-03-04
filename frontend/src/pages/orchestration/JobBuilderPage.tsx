/**
 * NovaSight Job Builder Page
 * ===========================
 *
 * Page for creating/editing Dagster jobs that run PySpark apps
 * on remote Spark clusters.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobService, CreateJobRequest, CreatePipelineRequest } from '@/services/jobService'
import { pysparkApi } from '@/services/pysparkApi'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CronBuilder } from '@/components/ui/cron-builder'
import {
  ArrowLeft,
  Save,
  Loader2,
  Database,
  Clock,
  Settings,
  Zap,
  GitBranch,
  Info,
  CheckCircle,
  Cpu,
  SlidersHorizontal,
} from 'lucide-react'
import { toast } from '@/components/ui/use-toast'

// Schedule presets
const schedulePresets = [
  { value: '@hourly', label: 'Hourly', description: 'Every hour' },
  { value: '@daily', label: 'Daily', description: 'Every day at midnight' },
  { value: '@weekly', label: 'Weekly', description: 'Every Monday at midnight' },
  { value: '@monthly', label: 'Monthly', description: 'First day of each month' },
]

export function JobBuilderPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEditing = !!jobId

  // Form state
  const [jobType, setJobType] = useState<'spark' | 'pipeline'>('spark')
  const [selectedAppId, setSelectedAppId] = useState<string>('')
  const [selectedAppIds, setSelectedAppIds] = useState<string[]>([])
  const [jobName, setJobName] = useState('')
  const [description, setDescription] = useState('')
  const [scheduleType, setScheduleType] = useState<'manual' | 'preset' | 'cron'>('manual')
  const [schedulePreset, setSchedulePreset] = useState('@daily')
  const [cronExpression, setCronExpression] = useState('0 0 * * *')
  const [parallel, setParallel] = useState(false)
  const [retries, setRetries] = useState(2)
  const [retryDelay, _setRetryDelay] = useState(5) // TODO: Implement UI
  const [notifyOnFailure, _setNotifyOnFailure] = useState(true) // TODO: Implement UI
  const [notifyOnSuccess, _setNotifyOnSuccess] = useState(false) // TODO: Implement UI
  const [notificationEmails, _setNotificationEmails] = useState('') // TODO: Implement UI

  // Resource configuration (per-job Spark resource allocation)
  const [driverMemory, setDriverMemory] = useState('2g')
  const [executorMemory, setExecutorMemory] = useState('2g')
  const [executorCores, setExecutorCores] = useState(2)
  const [numExecutors, setNumExecutors] = useState(2)
  const [additionalConfigs, setAdditionalConfigs] = useState('')

  // Load PySpark apps
  const { data: appsData, isLoading: loadingApps } = useQuery({
    queryKey: ['pyspark-apps'],
    queryFn: () => pysparkApi.list({ per_page: 100 }),
  })

  const pysparkApps = appsData?.apps || []

  // Load existing job if editing
  const { data: existingJob, isLoading: loadingJob } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobService.get(jobId!),
    enabled: isEditing,
  })

  // Populate form when editing
  useEffect(() => {
    if (existingJob) {
      setJobName(existingJob.dag_id)
      setDescription(existingJob.description || '')
      setJobType(existingJob.type)
      setScheduleType(existingJob.schedule_type)
      if (existingJob.schedule_preset) {
        setSchedulePreset(existingJob.schedule_preset)
      }
      if (existingJob.schedule_cron) {
        setCronExpression(existingJob.schedule_cron)
      }
      // Extract app IDs from tags
      const appIds = existingJob.tags.filter(
        (t) => t.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/)
      )
      if (existingJob.type === 'pipeline') {
        setSelectedAppIds(appIds)
      } else if (appIds.length > 0) {
        setSelectedAppId(appIds[0])
      }
    }
  }, [existingJob])

  // Auto-generate job name when app is selected
  useEffect(() => {
    if (!isEditing && selectedAppId && jobType === 'spark') {
      const app = pysparkApps.find((a) => a.id === selectedAppId)
      if (app) {
        const safeName = app.name.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_')
        setJobName(`spark_${safeName}`)
        setDescription(`Spark job for ${app.name}: ${app.source_table} → ${app.target_table}`)
      }
    }
  }, [selectedAppId, pysparkApps, isEditing, jobType])

  // Create/update mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      const schedule =
        scheduleType === 'manual'
          ? undefined
          : scheduleType === 'preset'
          ? schedulePreset
          : cronExpression

      // Build per-job spark resource config
      const additionalConfigsObj: Record<string, string> = {}
      additionalConfigs.split('\n').forEach((line) => {
        const [key, ...rest] = line.split('=')
        if (key?.trim() && rest.length > 0) {
          additionalConfigsObj[key.trim()] = rest.join('=').trim()
        }
      })
      const sparkResourceConfig: Record<string, unknown> = {
        driver_memory: driverMemory,
        executor_memory: executorMemory,
        executor_cores: executorCores,
        num_executors: numExecutors,
        ...(Object.keys(additionalConfigsObj).length > 0 && { additional_configs: additionalConfigsObj }),
      }

      if (jobType === 'spark') {
        const data: CreateJobRequest = {
          pyspark_app_id: selectedAppId,
          name: jobName,
          description,
          schedule,
          retries,
          retry_delay_minutes: retryDelay,
          spark_config: sparkResourceConfig,
          notifications: {
            emails: notificationEmails.split(',').map((e) => e.trim()).filter(Boolean),
            on_failure: notifyOnFailure,
            on_success: notifyOnSuccess,
          },
        }

        if (isEditing) {
          return jobService.update(jobId!, data)
        }
        return jobService.create(data)
      } else {
        const data: CreatePipelineRequest = {
          pyspark_app_ids: selectedAppIds,
          name: jobName,
          description,
          schedule,
          parallel,
          spark_config: sparkResourceConfig,
        }

        if (isEditing) {
          return jobService.update(jobId!, data as any)
        }
        return jobService.createPipeline(data)
      }
    },
    onSuccess: (job) => {
      toast({
        title: isEditing ? 'Job Updated' : 'Job Created',
        description: `Job "${job.dag_id}" has been ${isEditing ? 'updated' : 'created'} successfully.`,
      })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      navigate('/app/jobs')
    },
    onError: (err: Error) => {
      toast({
        title: 'Error',
        description: err.message,
        variant: 'destructive',
      })
    },
  })

  // Validation
  const isValid = () => {
    if (!jobName.trim()) return false
    if (jobType === 'spark' && !selectedAppId) return false
    if (jobType === 'pipeline' && selectedAppIds.length < 1) return false
    return true
  }

  const handleAppToggle = (appId: string) => {
    setSelectedAppIds((prev) =>
      prev.includes(appId) ? prev.filter((id) => id !== appId) : [...prev, appId]
    )
  }

  if ((isEditing && loadingJob) || loadingApps) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">
            {isEditing ? 'Edit Job' : 'Create Spark Job'}
          </h1>
          <p className="text-muted-foreground">
            {isEditing
              ? 'Modify job configuration'
              : 'Create a Dagster job that runs PySpark apps on remote Spark cluster'}
          </p>
        </div>
      </div>

      {/* Job Type Selection (only for new jobs) */}
      {!isEditing && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Job Type</CardTitle>
            <CardDescription>Choose whether to create a single job or a pipeline</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <Card
                className={`cursor-pointer transition-all ${
                  jobType === 'spark'
                    ? 'border-primary ring-2 ring-primary ring-offset-2'
                    : 'hover:border-primary/50'
                }`}
                onClick={() => setJobType('spark')}
              >
                <CardContent className="p-4 flex items-start gap-3">
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <Zap className="h-5 w-5 text-orange-600" />
                  </div>
                  <div>
                    <h3 className="font-medium">Single Spark Job</h3>
                    <p className="text-sm text-muted-foreground">
                      Run one PySpark app on your Spark cluster
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card
                className={`cursor-pointer transition-all ${
                  jobType === 'pipeline'
                    ? 'border-primary ring-2 ring-primary ring-offset-2'
                    : 'hover:border-primary/50'
                }`}
                onClick={() => setJobType('pipeline')}
              >
                <CardContent className="p-4 flex items-start gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <GitBranch className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <h3 className="font-medium">Pipeline</h3>
                    <p className="text-sm text-muted-foreground">
                      Run multiple PySpark apps in sequence or parallel
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </CardContent>
        </Card>
      )}

      {/* PySpark App Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Database className="h-5 w-5" />
            {jobType === 'spark' ? 'Select PySpark App' : 'Select PySpark Apps'}
          </CardTitle>
          <CardDescription>
            {jobType === 'spark'
              ? 'Choose the PySpark app to run'
              : 'Select multiple apps to include in the pipeline'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {pysparkApps.length === 0 ? (
            <div className="text-center py-8">
              <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No PySpark apps found</p>
              <Button variant="link" onClick={() => navigate('/app/pyspark/new')}>
                Create a PySpark App first
              </Button>
            </div>
          ) : jobType === 'spark' ? (
            <Select value={selectedAppId} onValueChange={setSelectedAppId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a PySpark app" />
              </SelectTrigger>
              <SelectContent>
                {pysparkApps.map((app) => (
                  <SelectItem key={app.id} value={app.id}>
                    <div className="flex flex-col">
                      <span>{app.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {app.source_table} → {app.target_table}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {pysparkApps.map((app) => (
                <div
                  key={app.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedAppIds.includes(app.id)
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted/50'
                  }`}
                  onClick={() => handleAppToggle(app.id)}
                >
                  <Checkbox
                    checked={selectedAppIds.includes(app.id)}
                    onCheckedChange={() => handleAppToggle(app.id)}
                  />
                  <div className="flex-1">
                    <p className="font-medium">{app.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {app.source_table} → {app.target_table}
                    </p>
                  </div>
                  {selectedAppIds.includes(app.id) && (
                    <Badge variant="secondary">
                      #{selectedAppIds.indexOf(app.id) + 1}
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          )}

          {jobType === 'pipeline' && selectedAppIds.length > 0 && (
            <div className="mt-4 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Switch checked={parallel} onCheckedChange={setParallel} id="parallel" />
                <Label htmlFor="parallel">Run in parallel</Label>
              </div>
              <p className="text-sm text-muted-foreground">
                {parallel
                  ? 'Apps will run simultaneously'
                  : 'Apps will run sequentially in selected order'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Job Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Job Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="jobName">Job Name *</Label>
              <Input
                id="jobName"
                value={jobName}
                onChange={(e) => setJobName(e.target.value)}
                placeholder="spark_my_extraction"
              />
              <p className="text-xs text-muted-foreground">
                Use lowercase letters, numbers, and underscores
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="retries">Retries on Failure</Label>
              <Input
                id="retries"
                type="number"
                min={0}
                max={10}
                value={retries}
                onChange={(e) => setRetries(parseInt(e.target.value) || 0)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this job does..."
              rows={2}
            />
          </div>
        </CardContent>
      </Card>

      {/* Schedule Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Schedule
          </CardTitle>
          <CardDescription>
            Configure when this job should run automatically
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs value={scheduleType} onValueChange={(v) => setScheduleType(v as any)}>
            <TabsList className="grid grid-cols-3 w-full max-w-md">
              <TabsTrigger value="manual">Manual</TabsTrigger>
              <TabsTrigger value="preset">Preset</TabsTrigger>
              <TabsTrigger value="cron">Custom Cron</TabsTrigger>
            </TabsList>

            <TabsContent value="manual" className="mt-4">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Info className="h-5 w-5" />
                <p>This job will only run when triggered manually</p>
              </div>
            </TabsContent>

            <TabsContent value="preset" className="mt-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {schedulePresets.map((preset) => (
                  <Card
                    key={preset.value}
                    className={`cursor-pointer transition-all ${
                      schedulePreset === preset.value
                        ? 'border-primary ring-2 ring-primary ring-offset-2'
                        : 'hover:border-primary/50'
                    }`}
                    onClick={() => setSchedulePreset(preset.value)}
                  >
                    <CardContent className="p-3 text-center">
                      {schedulePreset === preset.value && (
                        <CheckCircle className="h-4 w-4 text-primary mx-auto mb-1" />
                      )}
                      <p className="font-medium">{preset.label}</p>
                      <p className="text-xs text-muted-foreground">{preset.description}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="cron" className="mt-4">
              <CronBuilder value={cronExpression} onChange={setCronExpression} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Resource Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Resource Configuration
          </CardTitle>
          <CardDescription>
            Configure Spark resource allocation for this job. These override the global defaults.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="driverMemory">Driver Memory</Label>
              <Input
                id="driverMemory"
                value={driverMemory}
                onChange={(e) => setDriverMemory(e.target.value)}
                placeholder="2g"
              />
              <p className="text-xs text-muted-foreground">e.g. 1g, 2g, 4g, 512m</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="executorMemory">Executor Memory</Label>
              <Input
                id="executorMemory"
                value={executorMemory}
                onChange={(e) => setExecutorMemory(e.target.value)}
                placeholder="2g"
              />
              <p className="text-xs text-muted-foreground">e.g. 1g, 2g, 4g, 512m</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="executorCores">Executor Cores</Label>
              <Input
                id="executorCores"
                type="number"
                min={1}
                max={32}
                value={executorCores}
                onChange={(e) => setExecutorCores(parseInt(e.target.value) || 1)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="numExecutors">Number of Executors</Label>
              <Input
                id="numExecutors"
                type="number"
                min={1}
                max={100}
                value={numExecutors}
                onChange={(e) => setNumExecutors(parseInt(e.target.value) || 1)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5" />
            Advanced Configuration
          </CardTitle>
          <CardDescription>
            Additional Spark configuration properties (optional)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="additionalConfigs">Additional Spark Configs</Label>
            <Textarea
              id="additionalConfigs"
              value={additionalConfigs}
              onChange={(e) => setAdditionalConfigs(e.target.value)}
              placeholder={"spark.sql.shuffle.partitions=200\nspark.serializer=org.apache.spark.serializer.KryoSerializer"}
              rows={4}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              One config per line in key=value format. These are passed as --conf to spark-submit.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-between border-t pt-6">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Cancel
        </Button>
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={!isValid() || saveMutation.isPending}
        >
          {saveMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {isEditing ? 'Updating...' : 'Creating...'}
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              {isEditing ? 'Update Job' : 'Create Job'}
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

export default JobBuilderPage
