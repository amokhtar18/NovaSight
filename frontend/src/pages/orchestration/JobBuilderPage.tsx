/**
 * NovaSight Job Builder Page
 * ===========================
 *
 * Create / edit a Dagster job. The orchestrator schedules **only dlt
 * pipelines and dbt runs / tests** — Spark / PySpark scheduling has been
 * removed (see `app/domains/orchestration/domain/models.py::TaskType`).
 *
 * Job kinds:
 *   - **dlt**       — run a single dlt pipeline
 *   - **dbt_run**   — run dbt models (against the lake or warehouse profile)
 *   - **dbt_test**  — run dbt tests
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobService, CreateJobRequest, CreateDbtJobRequest } from '@/services/jobService'
import { pipelineService } from '@/services/pipelineService'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CronBuilder } from '@/components/ui/cron-builder'
import { PageHeader } from '@/components/common'
import {
  ArrowLeft,
  Save,
  Loader2,
  Database,
  Clock,
  Settings,
  Zap,
  Code2,
  FlaskConical,
  Info,
  CheckCircle,
} from 'lucide-react'
import { toast } from '@/components/ui/use-toast'

type JobKind = 'dlt' | 'dbt_run' | 'dbt_test'
type DbtProfile = 'default' | 'lake' | 'warehouse'
type ScheduleKind = 'manual' | 'preset' | 'cron'

const schedulePresets = [
  { value: '@hourly', label: 'Hourly', description: 'Every hour' },
  { value: '@daily', label: 'Daily', description: 'Every day at midnight' },
  { value: '@weekly', label: 'Weekly', description: 'Every Monday at midnight' },
  { value: '@monthly', label: 'Monthly', description: 'First day of each month' },
]

const kindMeta: Record<JobKind, { label: string; description: string; icon: JSX.Element; accent: string }> = {
  dlt: {
    label: 'dlt pipeline',
    description: 'Run a single dlt ingestion pipeline into the lake.',
    icon: <Zap className="h-5 w-5 text-orange-600" />,
    accent: 'border-orange-200 bg-orange-50',
  },
  dbt_run: {
    label: 'dbt run',
    description: 'Materialize dbt models on the lake or warehouse profile.',
    icon: <Code2 className="h-5 w-5 text-blue-600" />,
    accent: 'border-blue-200 bg-blue-50',
  },
  dbt_test: {
    label: 'dbt test',
    description: 'Run dbt tests against existing models.',
    icon: <FlaskConical className="h-5 w-5 text-purple-600" />,
    accent: 'border-purple-200 bg-purple-50',
  },
}

export function JobBuilderPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const isEditing = !!jobId

  // Common state
  const [jobKind, setJobKind] = useState<JobKind>('dlt')
  const [jobName, setJobName] = useState('')
  const [description, setDescription] = useState('')
  const [scheduleType, setScheduleType] = useState<ScheduleKind>('manual')
  const [schedulePreset, setSchedulePreset] = useState('@daily')
  const [cronExpression, setCronExpression] = useState('0 0 * * *')
  const [retries, setRetries] = useState(2)

  // dlt-specific
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>('')

  // dbt-specific
  const [dbtProfile, setDbtProfile] = useState<DbtProfile>('default')
  const [dbtSelectExpression, setDbtSelectExpression] = useState<string>('')
  const [dbtTags, setDbtTags] = useState<string>('')
  const [dbtFullRefresh, setDbtFullRefresh] = useState(false)
  const [dbtSplitByModel, setDbtSplitByModel] = useState(false)
  const [dbtLayers, setDbtLayers] = useState<string>('')
  const [dbtModelNames, setDbtModelNames] = useState<string>('')
  const [dbtUpstreamJobIds, setDbtUpstreamJobIds] = useState<string>('')
  const [dbtUpstreamTaskRefs, setDbtUpstreamTaskRefs] = useState<string>('')
  const [dbtDependsOn, setDbtDependsOn] = useState<string>('')

  // Load dlt pipelines
  const { data: pipelinesData, isLoading: loadingPipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => pipelineService.list({ per_page: 100 }),
  })
  const pipelines = pipelinesData?.items || []

  // Pre-fill from URL query params when arriving from the Scheduling page:
  //   ?pipeline_id=<uuid>            → dlt job for that pipeline
  //   ?kind=dbt_run|dbt_test         → dbt job
  //   ?select=<dbt selector>         → pre-fill --select expression
  //   ?name=<job name>               → pre-fill job name
  useEffect(() => {
    if (isEditing) return
    const pipelineParam = searchParams.get('pipeline_id')
    if (pipelineParam && !selectedPipelineId) {
      setSelectedPipelineId(pipelineParam)
      setJobKind('dlt')
    }
    const kindParam = searchParams.get('kind')
    if (kindParam === 'dbt_run' || kindParam === 'dbt_test') {
      setJobKind(kindParam)
    }
    const selectParam = searchParams.get('select')
    if (selectParam) {
      setDbtSelectExpression(selectParam)
    }
    const nameParam = searchParams.get('name')
    if (nameParam) {
      setJobName(nameParam)
    }
  }, [isEditing, searchParams, selectedPipelineId])

  // Load existing job if editing
  const { data: existingJob, isLoading: loadingJob } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobService.get(jobId!),
    enabled: isEditing,
  })

  // Populate form when editing
  useEffect(() => {
    if (!existingJob) return
    setJobName(existingJob.dag_id)
    setDescription(existingJob.description || '')
    setScheduleType(existingJob.schedule_type)
    if (existingJob.schedule_preset) setSchedulePreset(existingJob.schedule_preset)
    if (existingJob.schedule_cron) setCronExpression(existingJob.schedule_cron)

    // Map backend job type → form kind
    if (existingJob.type === 'dbt') {
      // Inspect tags for run vs test
      const isTest = existingJob.tags.includes('dbt_test')
      setJobKind(isTest ? 'dbt_test' : 'dbt_run')
      setDbtSplitByModel(existingJob.tags.includes('split:per_model'))
      const profileTag = existingJob.tags.find((t) =>
        ['profile:lake', 'profile:warehouse', 'profile:default'].includes(t)
      )
      if (profileTag) {
        setDbtProfile(profileTag.split(':')[1] as DbtProfile)
      }
    } else {
      setJobKind('dlt')
      const pipelineTag = existingJob.tags.find((t) =>
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(t)
      )
      if (pipelineTag) setSelectedPipelineId(pipelineTag)
    }
  }, [existingJob])

  // Auto-generate dlt job name
  useEffect(() => {
    if (isEditing || jobKind !== 'dlt' || !selectedPipelineId) return
    const p = pipelines.find((x) => x.id === selectedPipelineId)
    if (p) {
      const safe = p.name.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_')
      setJobName(`dlt_${safe}`)
      if (!description) {
        setDescription(`dlt pipeline run for ${p.name}`)
      }
    }
  }, [selectedPipelineId, pipelines, isEditing, jobKind, description])

  // Auto-generate dbt job name
  useEffect(() => {
    if (isEditing || jobKind === 'dlt' || jobName) return
    const verb = jobKind === 'dbt_test' ? 'test' : 'run'
    setJobName(`dbt_${verb}_${dbtProfile}`)
  }, [jobKind, dbtProfile, isEditing, jobName])

  const parseCsvOrNewlineList = (raw: string): string[] | undefined => {
    const values = raw
      .split(/[\n,]/)
      .map((value) => value.trim())
      .filter(Boolean)
    return values.length > 0 ? values : undefined
  }

  const parseUpstreamTaskRefs = (
    raw: string
  ): NonNullable<CreateDbtJobRequest['upstream_task_refs']> | undefined => {
    const refs = parseCsvOrNewlineList(raw)
    if (!refs) return undefined

    return refs.map((entry) => {
      const separator = entry.indexOf(':')
      if (separator <= 0 || separator >= entry.length - 1) {
        throw new Error(
          `Invalid upstream task reference "${entry}". Use job_or_dag:task_id.`
        )
      }

      const jobOrDag = entry.slice(0, separator).trim()
      const taskId = entry.slice(separator + 1).trim()

      if (!jobOrDag || !taskId) {
        throw new Error(
          `Invalid upstream task reference "${entry}". Use job_or_dag:task_id.`
        )
      }

      return {
        dag_id: jobOrDag,
        task_id: taskId,
      }
    })
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const schedule =
        scheduleType === 'manual'
          ? undefined
          : scheduleType === 'preset'
          ? schedulePreset
          : cronExpression

      if (jobKind === 'dlt') {
        const data: CreateJobRequest = {
          pipeline_id: selectedPipelineId,
          name: jobName,
          description,
          schedule,
          retries,
          retry_delay_minutes: 5,
        }
        return isEditing ? jobService.update(jobId!, data) : jobService.create(data)
      }

      // dbt_run / dbt_test
      const splitByModel = dbtSplitByModel
      const data: CreateDbtJobRequest = {
        kind: jobKind === 'dbt_test' ? 'test' : 'run',
        profile: dbtProfile,
        name: jobName,
        description,
        schedule,
        retries,
        retry_delay_minutes: 5,
        select: splitByModel ? undefined : dbtSelectExpression || undefined,
        tags: splitByModel
          ? undefined
          : dbtTags
          ? dbtTags.split(',').map((t) => t.trim()).filter(Boolean)
          : undefined,
        full_refresh: dbtFullRefresh,
        split_by_model: splitByModel,
        layers: splitByModel ? parseCsvOrNewlineList(dbtLayers) : undefined,
        model_names: splitByModel ? parseCsvOrNewlineList(dbtModelNames) : undefined,
        upstream_job_ids: parseCsvOrNewlineList(dbtUpstreamJobIds),
        upstream_task_refs: parseUpstreamTaskRefs(dbtUpstreamTaskRefs),
        depends_on: parseCsvOrNewlineList(dbtDependsOn),
      }
      return isEditing
        ? jobService.update(jobId!, data as unknown as Partial<CreateJobRequest>)
        : jobService.createDbtJob(data)
    },
    onSuccess: (job) => {
      toast({
        title: isEditing ? 'Job Updated' : 'Job Created',
        description: `Job "${job.dag_id}" has been ${isEditing ? 'updated' : 'created'} successfully.`,
      })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      navigate('/app/jobs')
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } }; message?: string })
          ?.response?.data?.error?.message ||
        (err as Error)?.message ||
        'Failed to save job'
      toast({ title: 'Error', description: msg, variant: 'destructive' })
    },
  })

  const isValid = (): boolean => {
    if (!jobName.trim()) return false
    if (jobKind === 'dlt' && !selectedPipelineId) return false
    return true
  }

  if ((isEditing && loadingJob) || loadingPipelines) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <PageHeader
        icon={kindMeta[jobKind].icon}
        title={isEditing ? 'Edit Job' : 'Create Job'}
        description={
          isEditing
            ? 'Modify job configuration'
            : 'Schedule a dlt pipeline or dbt run/test on Dagster'
        }
        eyebrow={
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Back
          </button>
        }
      />

      {/* Job Kind */}
      {!isEditing && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Job Type</CardTitle>
            <CardDescription>
              Choose what this job will execute. The orchestrator only schedules
              dlt pipelines and dbt jobs.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(Object.keys(kindMeta) as JobKind[]).map((k) => {
                const meta = kindMeta[k]
                const selected = jobKind === k
                return (
                  <Card
                    key={k}
                    className={`cursor-pointer transition-all ${
                      selected
                        ? 'border-primary ring-2 ring-primary ring-offset-2'
                        : 'hover:border-primary/50'
                    }`}
                    onClick={() => setJobKind(k)}
                  >
                    <CardContent className="p-4 flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${meta.accent}`}>{meta.icon}</div>
                      <div>
                        <h3 className="font-medium">{meta.label}</h3>
                        <p className="text-sm text-muted-foreground">{meta.description}</p>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* dlt-specific */}
      {jobKind === 'dlt' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Database className="h-5 w-5" />
              Select dlt Pipeline
            </CardTitle>
            <CardDescription>Choose the pipeline this job will run.</CardDescription>
          </CardHeader>
          <CardContent>
            {pipelines.length === 0 ? (
              <div className="text-center py-8">
                <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No dlt pipelines found</p>
                <Button variant="link" onClick={() => navigate('/app/pipelines/new')}>
                  Create a dlt pipeline first
                </Button>
              </div>
            ) : (
              <Select value={selectedPipelineId} onValueChange={setSelectedPipelineId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a dlt pipeline" />
                </SelectTrigger>
                <SelectContent>
                  {pipelines.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      <div className="flex flex-col">
                        <span>{p.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {p.source_table || p.iceberg_table_name || p.id}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </CardContent>
        </Card>
      )}

      {/* dbt-specific */}
      {(jobKind === 'dbt_run' || jobKind === 'dbt_test') && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              {jobKind === 'dbt_test' ? (
                <FlaskConical className="h-5 w-5" />
              ) : (
                <Code2 className="h-5 w-5" />
              )}
              {jobKind === 'dbt_test' ? 'dbt Test Configuration' : 'dbt Run Configuration'}
            </CardTitle>
            <CardDescription>
              {jobKind === 'dbt_test'
                ? 'Choose which tests to execute.'
                : 'Choose which models to materialize and on which profile.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {jobKind === 'dbt_run' && (
              <div className="space-y-2">
                <Label htmlFor="dbtProfile">Profile</Label>
                <Select
                  value={dbtProfile}
                  onValueChange={(v) => setDbtProfile(v as DbtProfile)}
                >
                  <SelectTrigger id="dbtProfile">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Default</SelectItem>
                    <SelectItem value="lake">Lake (DuckDB on Iceberg)</SelectItem>
                    <SelectItem value="warehouse">Warehouse (ClickHouse)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex items-center gap-2">
              <Switch
                id="splitByModel"
                checked={dbtSplitByModel}
                onCheckedChange={setDbtSplitByModel}
              />
              <Label htmlFor="splitByModel">Split by model</Label>
            </div>
            <p className="text-xs text-muted-foreground">
              Creates one task per discovered model. When enabled, model selector and tags are ignored.
            </p>

            {dbtSplitByModel && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="dbtLayers">Layers (optional)</Label>
                  <Input
                    id="dbtLayers"
                    value={dbtLayers}
                    onChange={(e) => setDbtLayers(e.target.value)}
                    placeholder="staging, marts"
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated dbt model folders to include.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="dbtModelNames">Model names (optional)</Label>
                  <Input
                    id="dbtModelNames"
                    value={dbtModelNames}
                    onChange={(e) => setDbtModelNames(e.target.value)}
                    placeholder="customers, orders"
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated model names to include.
                  </p>
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="dbtSelect">
                {jobKind === 'dbt_test' ? 'Test Selector' : 'Model Selector'} (optional)
              </Label>
              <Input
                id="dbtSelect"
                value={dbtSelectExpression}
                onChange={(e) => setDbtSelectExpression(e.target.value)}
                disabled={dbtSplitByModel}
                placeholder={
                  jobKind === 'dbt_test'
                    ? 'e.g. orders, source:raw.* (defaults to all)'
                    : 'e.g. fct_orders+ (defaults to all models)'
                }
              />
              <p className="text-xs text-muted-foreground">
                Passed to dbt as <code>--select</code>. Leave empty to run everything.
              </p>
            </div>

            {jobKind === 'dbt_run' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="dbtTags">Tags (optional)</Label>
                  <Input
                    id="dbtTags"
                    value={dbtTags}
                    onChange={(e) => setDbtTags(e.target.value)}
                    disabled={dbtSplitByModel}
                    placeholder="hourly, marts (comma-separated)"
                  />
                  <p className="text-xs text-muted-foreground">
                    If provided, takes precedence over the model selector.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    id="fullRefresh"
                    checked={dbtFullRefresh}
                    onCheckedChange={setDbtFullRefresh}
                  />
                  <Label htmlFor="fullRefresh">Full refresh</Label>
                </div>
              </>
            )}

            <div className="space-y-2 pt-2">
              <Label htmlFor="upstreamJobIds">Upstream jobs (optional)</Label>
              <Input
                id="upstreamJobIds"
                value={dbtUpstreamJobIds}
                onChange={(e) => setDbtUpstreamJobIds(e.target.value)}
                placeholder="job_uuid_or_dag_id_1, job_uuid_or_dag_id_2"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated existing job ids or dag ids. New tasks depend on terminal tasks from these jobs.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="upstreamTaskRefs">Upstream task refs (optional)</Label>
              <Textarea
                id="upstreamTaskRefs"
                value={dbtUpstreamTaskRefs}
                onChange={(e) => setDbtUpstreamTaskRefs(e.target.value)}
                rows={2}
                placeholder="job_or_dag:task_id, another_job:task_id"
              />
              <p className="text-xs text-muted-foreground">
                Use job_or_dag:task_id entries, separated by commas or new lines.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="dependsOn">Raw depends_on refs (optional)</Label>
              <Input
                id="dependsOn"
                value={dbtDependsOn}
                onChange={(e) => setDbtDependsOn(e.target.value)}
                placeholder="task_id, job:other_dag:task_id"
              />
              <p className="text-xs text-muted-foreground">
                Additional dependency refs appended to created tasks.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Job metadata */}
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
                placeholder="dlt_orders_hourly"
              />
              <p className="text-xs text-muted-foreground">
                Use lowercase letters, numbers, and underscores.
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

      {/* Schedule */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Schedule
          </CardTitle>
          <CardDescription>
            Configure when this job should run automatically.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs value={scheduleType} onValueChange={(v) => setScheduleType(v as ScheduleKind)}>
            <TabsList className="grid grid-cols-3 w-full max-w-md">
              <TabsTrigger value="manual">Manual</TabsTrigger>
              <TabsTrigger value="preset">Preset</TabsTrigger>
              <TabsTrigger value="cron">Custom Cron</TabsTrigger>
            </TabsList>

            <TabsContent value="manual" className="mt-4">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Info className="h-5 w-5" />
                <p>This job will only run when triggered manually.</p>
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
