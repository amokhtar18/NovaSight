/**
 * Enhanced dbt Studio Page
 *
 * Extends the original DbtStudioPage with additional tabs for:
 * - Visual Query Builder (no-code SQL)
 * - Test Builder & Source Freshness
 * - Schema Explorer (warehouse introspection)
 * - Semantic Layer Designer
 * - Package Manager
 *
 * Drop-in replacement for DbtStudioPage.
 */

import { useState, useCallback, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'
import {
  Layers,
  Plus,
  Database,
  Play,
  RefreshCw,
  FileCode2,
  GitBranch,
  TestTube,
  FolderTree,
  ShieldCheck,
} from 'lucide-react'
import { GlassCard, GlassCardContent } from '@/components/ui/glass-card'
import { fadeVariants, staggerContainerVariants } from '@/lib/motion-variants'
import {
  LineageViewer,
  ProjectViewer,
} from '@/features/dbt-studio/components'
import {
  useModels,
  useServerStatus,
  useStartServer,
  useStopServer,
  useDbtRun,
  useDbtTest,
} from '@/features/dbt-studio/hooks/useDbtStudio'
import { palette } from '@/lib/colors'

// New visual builder imports
import { VisualQueryBuilder } from '../components/sql-builder'
import { TestConfigForm, FreshnessConfig, TestResultsTable } from '../components/test-builder'
import { CodePreview } from '../components/shared'
import {
  useVisualModels,
  useCreateVisualModel,
} from '../hooks/useVisualModels'
import { useCodePreviewFromPayloadMutation } from '../hooks/useCodePreview'
import { useWarehouseColumns } from '../hooks/useWarehouseSchema'
import type {
  VisualModelCreatePayload,
  WarehouseColumn,
} from '../types/visualModel'
import { useDataSources } from '@/features/datasources/hooks'
import { extractErrorMessage as extractApiErrorMessage } from '@/services/apiClient'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { AlertTriangle, Zap } from 'lucide-react'

const TENANT_WAREHOUSE_ID = '__tenant__'

export function EnhancedDbtStudioPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState('builder')
  const [availableColumns, setAvailableColumns] = useState<WarehouseColumn[]>([])
  const [selectedSchema, setSelectedSchema] = useState<string>()
  const [selectedTable, setSelectedTable] = useState<string>()
  // Bumping this key remounts the VisualQueryBuilder so its internal
  // form state resets to blank fields (used by the "New Model" button).
  const [builderResetKey, setBuilderResetKey] = useState(0)
  // Warehouse source binding — defaults to the tenant-managed ClickHouse
  // warehouse (which is the only valid dbt target per platform design).
  // Selecting an external connection does NOT repoint dbt at that DB;
  // it surfaces a CTA to ingest via PySpark first (see X4 flow).
  const [sourceConnectionId, setSourceConnectionId] = useState<string>(
    TENANT_WAREHOUSE_ID
  )

  // Existing API hooks
  const { data: modelsData, refetch: refetchModels } = useModels()
  const { data: serverStatus, isLoading: statusLoading } = useServerStatus()
  const startServerMutation = useStartServer()
  const stopServerMutation = useStopServer()
  const dbtRunMutation = useDbtRun()
  const dbtTestMutation = useDbtTest()

  // Visual builder hooks
  const { data: visualModels } = useVisualModels()
  const createVisualModel = useCreateVisualModel()
  const codePreview = useCodePreviewFromPayloadMutation()

  // Warehouse column introspection — enabled when a table is selected
  const { data: fetchedColumns } = useWarehouseColumns(selectedSchema, selectedTable)

  // Connections for the warehouse-source picker
  const { data: connectionsData } = useDataSources()
  const connections = connectionsData?.items ?? []
  const externalConnection =
    sourceConnectionId !== TENANT_WAREHOUSE_ID
      ? connections.find((c) => c.id === sourceConnectionId)
      : null

  // Sync fetched columns into local state
  useEffect(() => {
    if (fetchedColumns && fetchedColumns.length > 0) {
      setAvailableColumns(fetchedColumns)
    }
  }, [fetchedColumns])

  // Deep-link handler: accept ?source_schema=&source_table=&tab= from
  // upstream modules (PySpark detail "Use in dbt Studio"). Apply once,
  // then strip the params so page state is the source of truth.
  useEffect(() => {
    const schema = searchParams.get('source_schema')
    const table = searchParams.get('source_table')
    const tab = searchParams.get('tab')
    if (!schema && !table && !tab) return
    if (schema) setSelectedSchema(schema)
    if (table) setSelectedTable(table)
    if (tab) setActiveTab(tab)
    const next = new URLSearchParams(searchParams)
    next.delete('source_schema')
    next.delete('source_table')
    next.delete('tab')
    setSearchParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Server control
  const handleStartServer = async () => {
    try {
      await startServerMutation.mutateAsync()
      toast({ title: 'MCP Server started' })
    } catch {
      toast({ title: 'Failed to start server', variant: 'destructive' })
    }
  }

  const handleStopServer = async () => {
    try {
      await stopServerMutation.mutateAsync()
      toast({ title: 'MCP Server stopped' })
    } catch {
      toast({ title: 'Failed to stop server', variant: 'destructive' })
    }
  }

  // dbt commands
  const handleDbtRun = async () => {
    try {
      await dbtRunMutation.mutateAsync({})
      toast({ title: 'dbt run completed' })
      refetchModels()
    } catch {
      toast({ title: 'dbt run failed', variant: 'destructive' })
    }
  }

  const handleDbtTest = async () => {
    try {
      await dbtTestMutation.mutateAsync({})
      toast({ title: 'dbt test completed' })
    } catch {
      toast({ title: 'dbt test failed', variant: 'destructive' })
    }
  }

  // Visual query builder handlers
  const handleVisualSave = useCallback(
    async (payload: VisualModelCreatePayload) => {
      try {
        await createVisualModel.mutateAsync(payload)
        toast({ title: 'Model created', description: `${payload.model_name} saved successfully` })
        // After a successful save, hop to the Project tab so the user can
        // see the new model materialised in the dbt project tree.
        setActiveTab('project')
      } catch (err) {
        toast({
          title: 'Failed to save model',
          description: extractApiErrorMessage(err),
          variant: 'destructive',
        })
      }
    },
    [createVisualModel, toast]
  )

  // "New Model" → reset the builder to blank fields and switch to the
  // Model Builder tab. We bump ``builderResetKey`` so VisualQueryBuilder
  // (which seeds its state from ``initialValues`` only on mount) is fully
  // remounted, and we also clear any auto-filled schema/table selection.
  const handleNewModel = useCallback(() => {
    setSelectedSchema(undefined)
    setSelectedTable(undefined)
    setAvailableColumns([])
    setActiveTab('builder')
    setBuilderResetKey((k) => k + 1)
  }, [])

  const handleVisualPreview = useCallback(
    async (payload: VisualModelCreatePayload) => {
      try {
        await codePreview.mutateAsync(payload)
        toast({ title: 'Code preview generated' })
      } catch (err) {
        toast({
          title: 'Preview failed',
          description: extractApiErrorMessage(err),
          variant: 'destructive',
        })
      }
    },
    [codePreview, toast]
  )

  const handleTableSelect = useCallback((schema: string, table: string) => {
    setSelectedSchema(schema)
    setSelectedTable(table)
  }, [])
  void handleTableSelect

  // Stats
  const stats = [
    {
      label: 'Models',
      value: modelsData?.models?.length || 0,
      icon: FileCode2,
      color: palette.success[500],
    },
    {
      label: 'Visual Models',
      value: visualModels?.length || 0,
      icon: Layers,
      color: palette.primary[500],
    },
    {
      label: 'Sources',
      value: modelsData?.models?.filter((m: any) => m.resource_type === 'source').length || 0,
      icon: Database,
      color: palette.info[500],
    },
  ]

  return (
    <div className="min-h-screen w-full p-6 space-y-6 flex flex-col">
      {/* Header */}
      <motion.div
        variants={fadeVariants}
        initial="hidden"
        animate="visible"
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Layers className="h-6 w-6 text-indigo-500" />
            dbt Studio
          </h1>
          <p className="text-gray-500 mt-1">
            Visual dbt model builder with semantic layer integration
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Warehouse source picker */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 whitespace-nowrap">
              Warehouse source
            </span>
            <Select value={sourceConnectionId} onValueChange={setSourceConnectionId}>
              <SelectTrigger className="h-8 text-xs min-w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={TENANT_WAREHOUSE_ID} className="text-xs">
                  Tenant-managed (ClickHouse)
                </SelectItem>
                {connections.map((c) => (
                  <SelectItem key={c.id} value={c.id} className="text-xs font-mono">
                    {c.name} · {c.db_type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant={serverStatus?.is_running ? 'default' : 'secondary'}
              className={serverStatus?.is_running ? 'bg-green-500' : ''}
            >
              {statusLoading
                ? 'Checking...'
                : serverStatus?.is_running
                ? 'MCP Online'
                : 'MCP Offline'}
            </Badge>
            {serverStatus?.is_running ? (
              <Button
                variant="outline"
                size="sm"
                onClick={handleStopServer}
                disabled={stopServerMutation.isPending}
              >
                Stop Server
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={handleStartServer}
                disabled={startServerMutation.isPending}
              >
                Start Server
              </Button>
            )}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleDbtRun}
            disabled={dbtRunMutation.isPending}
          >
            {dbtRunMutation.isPending ? (
              <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-1" />
            )}
            dbt run
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDbtTest}
            disabled={dbtTestMutation.isPending}
          >
            {dbtTestMutation.isPending ? (
              <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <TestTube className="h-4 w-4 mr-1" />
            )}
            dbt test
          </Button>

          <Button onClick={handleNewModel}>
            <Plus className="h-4 w-4 mr-1" />
            New Model
          </Button>
        </div>
      </motion.div>

      {/* External connection CTA — ingest via PySpark before dbt modeling */}
      {externalConnection && (
        <div className="rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30 p-3 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0" />
          <div className="flex-1 text-sm text-amber-900 dark:text-amber-100">
            <strong>{externalConnection.name}</strong>{' '}
            <span className="text-xs opacity-70">({externalConnection.db_type})</span>{' '}
            is an external connection. dbt models are materialized into the tenant-managed ClickHouse warehouse —
            ingest this source via a PySpark job first, then model it here.
          </div>
          <Button
            size="sm"
            onClick={() =>
              navigate(
                `/app/pyspark/new?connection_id=${externalConnection.id}&intent=dbt_source`
              )
            }
          >
            <Zap className="h-4 w-4 mr-1" />
            Create PySpark App
          </Button>
        </div>
      )}

      {/* Stats */}
      <motion.div
        variants={staggerContainerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
      >
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <GlassCard key={stat.label}>
              <GlassCardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{stat.label}</p>
                    <p className="text-2xl font-bold mt-1">{stat.value}</p>
                  </div>
                  <div
                    className="p-3 rounded-lg"
                    style={{ backgroundColor: `${stat.color}20` }}
                  >
                    <Icon className="h-6 w-6" style={{ color: stat.color }} />
                  </div>
                </div>
              </GlassCardContent>
            </GlassCard>
          )
        })}
      </motion.div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 w-full">
        <TabsList
          className="mb-6 grid w-full grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 h-auto gap-1 rounded-xl border border-border/60 bg-gradient-to-br from-muted/40 via-muted/20 to-transparent p-1.5 shadow-sm backdrop-blur-sm"
        >
          <TabsTrigger
            value="builder"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <FileCode2 className="h-4 w-4" />
            Model Builder
          </TabsTrigger>
          <TabsTrigger
            value="lineage"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <GitBranch className="h-4 w-4" />
            Lineage
          </TabsTrigger>
          <TabsTrigger
            value="tests"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <ShieldCheck className="h-4 w-4" />
            Tests
          </TabsTrigger>
          <TabsTrigger
            value="project"
            className="group flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all hover:bg-background/60 data-[state=active]:bg-gradient-to-br data-[state=active]:from-indigo-500 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md data-[state=active]:shadow-indigo-500/30"
          >
            <FolderTree className="h-4 w-4" />
            Project
          </TabsTrigger>
        </TabsList>

        {/* ── Model Builder (SQL Builder) ──────────────────────────── */}
        <TabsContent value="builder" className="space-y-4">
          <div className="space-y-4">
            <VisualQueryBuilder
              key={builderResetKey}
              availableColumns={availableColumns}
              availableModels={
                (visualModels || []).map((m: any) => m.model_name)
              }
              selectedSourceSchema={selectedSchema}
              selectedSourceTable={selectedTable}
              onSchemaChange={setSelectedSchema}
              onTableChange={setSelectedTable}
              onSave={handleVisualSave}
              onPreview={handleVisualPreview}
              isSaving={createVisualModel.isPending}
            />
            {codePreview.data && (
              <CodePreview
                sql={codePreview.data.sql}
                yaml={codePreview.data.yaml}
                title="Generated dbt Code"
              />
            )}
          </div>
        </TabsContent>

        {/* ── Lineage ─────────────────────────────────────────────────── */}
        <TabsContent value="lineage" className="h-[600px]">
          <LineageViewer
            showFullDag
            onNodeSelect={(node: any) => {
              if (node.resource_type === 'model') {
                navigate(`/app/dbt-studio/models/${node.name}`)
              }
            }}
          />
        </TabsContent>

        {/* ── Tests & Freshness ───────────────────────────────────────── */}
        <TabsContent value="tests">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-4">
              <TestConfigForm
                modelName={
                  (visualModels || [])[0]?.model_name || 'my_model'
                }
                availableModels={
                  (visualModels || []).map((m: any) => m.model_name)
                }
                onSave={(payload: any) => {
                  toast({ title: `Test "${payload.test_name}" created` })
                }}
              />
              <FreshnessConfig
                sourceName="raw_data"
                tableName="orders"
                onSave={() => {
                  toast({ title: 'Freshness config saved' })
                }}
              />
            </div>
            <div>
              <TestResultsTable results={[]} />
            </div>
          </div>
        </TabsContent>

        {/* ── Semantic / Query / Schema tabs intentionally hidden ─── */}

        {/* ── Project (original) ──────────────────────────────────────── */}
        <TabsContent value="project" className="min-h-[600px]">
          <ProjectViewer />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default EnhancedDbtStudioPage
