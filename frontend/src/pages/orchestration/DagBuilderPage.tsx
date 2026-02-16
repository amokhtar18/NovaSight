import { useCallback, useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactFlow, {
  Node,
  Controls,
  Background,
  MiniMap,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuth } from '@/contexts/AuthContext'
import { dagService, TaskConfig } from '@/services/dagService'
import { pysparkApi } from '@/services/pysparkApi'
import { CronBuilder } from '@/components/ui/cron-builder'
import { DagCodePreview } from '@/components/ui/dag-code-preview'
import type { PySparkApp } from '@/types/pyspark'
import {
  Play,
  ArrowLeft,
  Database,
  Code2,
  Mail,
  Timer,
  Terminal,
  Loader2,
  Sparkles,
  Tag,
  Trash2,
  Eye,
} from 'lucide-react'

const taskTypes = [
  { type: 'spark_submit', label: 'Spark Submit', icon: Database, color: '#ef4444' },
  { type: 'dbt_run', label: 'dbt Run', icon: Code2, color: '#10b981' },
  { type: 'dbt_test', label: 'dbt Test', icon: Code2, color: '#06b6d4' },
  { type: 'email', label: 'Email', icon: Mail, color: '#8b5cf6' },
  { type: 'http_sensor', label: 'HTTP Sensor', icon: Timer, color: '#f59e0b' },
  { type: 'bash_operator', label: 'Bash Script', icon: Terminal, color: '#6b7280' },
]

export function DagBuilderPage() {
  const { dagId } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const { user } = useAuth()
  const isEditing = !!dagId

  const [dagName, setDagName] = useState(dagId || '')
  const [description, setDescription] = useState('')
  const [dagTags, setDagTags] = useState<string[]>([])
  const [cronExpression, setCronExpression] = useState('')
  const [timezone, setTimezone] = useState('UTC')
  
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isTriggering, setIsTriggering] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [previewCode, setPreviewCode] = useState('')
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    errors: string[]
  }>({ valid: true, errors: [] })
  
  // Get tenant name for auto-tagging
  const tenantName = user?.tenant_name || 'default'
  const tenantSlug = tenantName.toLowerCase().replace(/\s+/g, '-')
  
  // PySpark apps for Spark Submit task configuration
  const [pysparkApps, setPysparkApps] = useState<PySparkApp[]>([])
  const [loadingApps, setLoadingApps] = useState(false)
  const [taskConfigs, setTaskConfigs] = useState<Record<string, Record<string, unknown>>>({})
  
  // Default Spark master URL (can be configured via environment)
  const defaultSparkMaster = 'spark://spark-master:7077'
  
  // Initialize tenant tag on mount
  useEffect(() => {
    if (tenantSlug && !dagTags.includes(tenantSlug)) {
      setDagTags(prev => [...prev, tenantSlug])
    }
  }, [tenantSlug])
  
  // Load PySpark apps on component mount
  useEffect(() => {
    setLoadingApps(true)
    pysparkApi.list({ per_page: 100 })
      .then(response => {
        console.log('[DagBuilder] PySpark apps loaded:', response)
        setPysparkApps(response.apps || [])
      })
      .catch(err => {
        console.error('Failed to load PySpark apps:', err)
      })
      .finally(() => setLoadingApps(false))
  }, [])
  
  // Update task config and auto-fill fields when PySpark app is selected
  const updateTaskConfig = (nodeId: string, key: string, value: unknown) => {
    setTaskConfigs(prev => {
      const updated = {
        ...prev,
        [nodeId]: {
          ...(prev[nodeId] || {}),
          [key]: value
        }
      }
      
      // If a PySpark app is selected, auto-fill the app path, spark master, and DAG name
      if (key === 'pyspark_app_id' && value) {
        const selectedApp = pysparkApps.find(app => app.id === value)
        if (selectedApp) {
          // Auto-fill application path based on generated code location
          const appNameSlug = selectedApp.name.toLowerCase().replace(/\s+/g, '_')
          const appPath = `/opt/spark/jobs/${appNameSlug}.py`
          updated[nodeId] = {
            ...updated[nodeId],
            application_path: appPath,
            spark_master: defaultSparkMaster,
            app_name: selectedApp.name,
          }
          
          // Auto-name the DAG based on PySpark app
          const generatedDagName = `${appNameSlug}_pipeline`
          setDagName(generatedDagName)
          setDescription(`Data pipeline for ${selectedApp.name} - extracting from ${selectedApp.source_table} to ${selectedApp.target_table}`)
          
          // Add pyspark tag if not already present
          setDagTags(prev => {
            const newTags = [...prev]
            if (!newTags.includes('pyspark')) newTags.push('pyspark')
            if (!newTags.includes('etl')) newTags.push('etl')
            return newTags
          })
        }
      }
      
      return updated
    })
  }

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            type: 'smoothstep',
            animated: true,
            style: { stroke: '#6366f1' },
          },
          eds
        )
      )
    },
    [setEdges]
  )

  const onDragStart = (event: React.DragEvent, taskType: string) => {
    event.dataTransfer.setData('application/tasktype', taskType)
    event.dataTransfer.effectAllowed = 'move'
  }

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      const taskType = event.dataTransfer.getData('application/tasktype')
      if (!taskType) return

      const taskDef = taskTypes.find((t) => t.type === taskType)
      if (!taskDef) return

      const reactFlowBounds = event.currentTarget.getBoundingClientRect()
      const position = {
        x: event.clientX - reactFlowBounds.left - 75,
        y: event.clientY - reactFlowBounds.top - 25,
      }

      const newId = `${taskType}_${Date.now()}`
      const newNode: Node = {
        id: newId,
        position,
        data: { label: taskDef.label, taskType },
        style: {
          background: taskDef.color,
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '10px 20px',
          fontWeight: 500,
        },
      }

      setNodes((nds) => [...nds, newNode])
    },
    [setNodes]
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
  }, [])

  // Click on canvas (not on node) to deselect and show DAG config
  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  // Delete a task node
  const deleteTask = (nodeId: string) => {
    setNodes(nds => nds.filter(n => n.id !== nodeId))
    setEdges(eds => eds.filter(e => e.source !== nodeId && e.target !== nodeId))
    setTaskConfigs(prev => {
      const updated = { ...prev }
      delete updated[nodeId]
      return updated
    })
    setSelectedNode(null)
    toast({
      title: 'Task Removed',
      description: 'Task has been removed from the DAG',
    })
  }

  // Convert ReactFlow nodes to TaskConfig format
  const nodesToTasks = (): TaskConfig[] => {
    return nodes.map((node) => {
      // Find dependencies based on edges
      const dependencies = edges
        .filter((edge) => edge.target === node.id)
        .map((edge) => edge.source)

      const config = taskConfigs[node.id] || {}
      
      // Generate meaningful task_id from app_name, target_table, or fallback to node.id
      let taskId = node.id
      if (config.app_name) {
        // Use app_name (from PySpark app) as task ID
        const appNameSlug = (config.app_name as string).toLowerCase().replace(/\s+/g, '_')
        taskId = `${appNameSlug}_task`
      } else if (config.pyspark_app_id) {
        // Try to get table name from selected PySpark app
        const selectedApp = pysparkApps.find(app => app.id === config.pyspark_app_id)
        if (selectedApp?.target_table) {
          taskId = `${selectedApp.target_table.toLowerCase().replace(/\s+/g, '_')}_task`
        }
      }

      return {
        task_id: taskId,
        task_type: node.data.taskType,
        config: config,
        timeout_minutes: (config.timeout_minutes as number) || 60,
        retries: (config.retries as number) || 1,
        retry_delay_minutes: 5,
        trigger_rule: 'all_success',
        depends_on: dependencies.map(depId => {
          // Also convert dependency IDs to meaningful names
          const depConfig = taskConfigs[depId] || {}
          if (depConfig.app_name) {
            return `${(depConfig.app_name as string).toLowerCase().replace(/\s+/g, '_')}_task`
          }
          return depId
        }),
        position_x: node.position.x,
        position_y: node.position.y,
      }
    })
  }

  // Validate DAG configuration
  const validateDag = (): { valid: boolean; errors: string[] } => {
    const errors: string[] = []

    if (!dagName.trim()) {
      errors.push('DAG name is required')
    } else if (!/^[a-z][a-z0-9_]*$/.test(dagName)) {
      errors.push('DAG name must start with a letter and contain only lowercase letters, numbers, and underscores')
    }

    if (nodes.length === 0) {
      errors.push('Add at least one task to the DAG')
    }

    // Validate each task
    nodes.forEach((node) => {
      const config = taskConfigs[node.id] || {}
      
      if (node.data.taskType === 'spark_submit') {
        if (!config.application_path && !config.pyspark_app_id) {
          errors.push(`Task "${node.id}": Application path is required for Spark Submit`)
        }
      }
    })

    // Check for circular dependencies
    const visited = new Set<string>()
    const recursionStack = new Set<string>()
    
    const hasCycle = (nodeId: string): boolean => {
      visited.add(nodeId)
      recursionStack.add(nodeId)
      
      const outEdges = edges.filter(e => e.source === nodeId)
      for (const edge of outEdges) {
        if (!visited.has(edge.target)) {
          if (hasCycle(edge.target)) return true
        } else if (recursionStack.has(edge.target)) {
          return true
        }
      }
      
      recursionStack.delete(nodeId)
      return false
    }
    
    for (const node of nodes) {
      if (!visited.has(node.id) && hasCycle(node.id)) {
        errors.push('DAG contains circular dependencies')
        break
      }
    }

    return { valid: errors.length === 0, errors }
  }

  // Generate DAG code preview
  const generateDagCode = (): string => {
    const tasks = nodesToTasks()
    const imports = new Set<string>([
      'from __future__ import annotations',
      'from datetime import datetime, timedelta',
      'import os',
      'import pendulum',
      'from airflow.models.dag import DAG',
      'from airflow.operators.empty import EmptyOperator',
    ])

    // Add task-specific imports
    let hasSparkSubmit = false
    tasks.forEach(task => {
      switch (task.task_type) {
        case 'spark_submit':
          imports.add('from airflow.operators.bash import BashOperator')
          imports.add('from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator')
          imports.add('from airflow.utils.trigger_rule import TriggerRule')
          hasSparkSubmit = true
          break
        case 'dbt_run':
        case 'dbt_test':
          imports.add('from airflow.operators.bash import BashOperator')
          break
        case 'email':
          imports.add('from airflow.providers.smtp.operators.smtp import EmailOperator')
          break
        case 'http_sensor':
          imports.add('from airflow.providers.http.sensors.http import HttpSensor')
          break
        case 'bash_operator':
          imports.add('from airflow.operators.bash import BashOperator')
          break
      }
    })

    const taskCode = tasks.map(task => generateTaskCode(task)).join('\n\n')
    const depCode = generateDependencyCode(tasks)

    // Use tenant slug for owner
    const ownerName = tenantSlug || 'novasight'
    
    const dagCode = `"""
Auto-generated NovaSight DAG
============================

DAG ID: ${dagName}
Generated by NovaSight DAG Builder
Owner: ${ownerName}
Tags: ${dagTags.join(', ')}

WARNING: This file is auto-generated by NovaSight.
Do not edit manually - changes will be overwritten.

Spark submission: Uses native SparkSubmitOperator (preferred) or docker exec fallback.
"""

${Array.from(imports).join('\n')}

# ============================================
# Spark Configuration
# ============================================
SPARK_HOME = os.environ.get('SPARK_HOME', '/opt/spark')
SPARK_MASTER = os.environ.get('SPARK_MASTER', 'spark://spark-master:7077')
SPARK_MASTER_CONTAINER = os.environ.get('SPARK_MASTER_CONTAINER', 'novasight-spark-master')

# Check if native Spark is available (preferred)
SPARK_NATIVE_AVAILABLE = os.path.exists(f'{SPARK_HOME}/bin/spark-submit')

default_args = {
    'owner': '${ownerName}',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='${dagName}',
    default_args=default_args,
    description='${description || ''}',
    schedule=${cronExpression ? `'${cronExpression}'` : 'None'},
    start_date=pendulum.datetime(2024, 1, 1, tz='${timezone}'),
    catchup=False,
    tags=${JSON.stringify(dagTags)},
) as dag:
    
    # Start task
    start = EmptyOperator(task_id='start')
    
    # End task  
    end = EmptyOperator(task_id='end')
    
    # Task definitions
    tasks = {}
    
${taskCode}

# ============================================
# Task Dependencies
# ============================================
# Dependencies are set at the end after all tasks are defined
# to ensure proper resolution regardless of conditional task creation
${depCode}
`
    return dagCode
  }

  const generateTaskCode = (task: TaskConfig): string => {
    const indent = '    '
    const config = task.config as Record<string, unknown>
    
    switch (task.task_type) {
      case 'spark_submit': {
        const appPath = config.application_path || '/opt/spark/jobs/job.py'
        const driverMemory = (config.driver_memory as string) || '1g'
        const executorMemory = (config.executor_memory as string) || '2g'
        const executorCores = (config.executor_cores as number) || 2
        return `${indent}# Spark Submit Task: ${task.task_id}
${indent}# Hybrid execution: Native SparkSubmitOperator (preferred) or docker exec fallback
${indent}if SPARK_NATIVE_AVAILABLE:
${indent}    # Use native SparkSubmitOperator (preferred)
${indent}    tasks['${task.task_id}'] = SparkSubmitOperator(
${indent}        task_id='${task.task_id}',
${indent}        application='${appPath}',
${indent}        conn_id='spark_default',
${indent}        executor_memory='${executorMemory}',
${indent}        executor_cores=${executorCores},
${indent}        driver_memory='${driverMemory}',
${indent}        conf={
${indent}            'spark.executor.memory': '${executorMemory}',
${indent}            'spark.executor.cores': '${executorCores}',
${indent}        },
${indent}        execution_timeout=timedelta(minutes=${task.timeout_minutes}),
${indent}    )
${indent}else:
${indent}    # Fallback to docker exec
${indent}    ${task.task_id}_cmd = f"""
${indent}docker exec {SPARK_MASTER_CONTAINER} /opt/spark/bin/spark-submit \\\\
${indent}    --master spark://spark-master:7077 \\\\
${indent}    --deploy-mode client \\\\
${indent}    --driver-memory ${driverMemory} \\\\
${indent}    --executor-memory ${executorMemory} \\\\
${indent}    --executor-cores ${executorCores} \\\\
${indent}    --jars /opt/spark/jars/custom/postgresql-42.7.4.jar,/opt/spark/jars/custom/clickhouse-jdbc-0.6.3.jar \\\\
${indent}    ${appPath}
${indent}"""
${indent}    tasks['${task.task_id}'] = BashOperator(
${indent}        task_id='${task.task_id}',
${indent}        bash_command=${task.task_id}_cmd,
${indent}        execution_timeout=timedelta(minutes=${task.timeout_minutes}),
${indent}    )`
      }

      case 'dbt_run':
        return `${indent}tasks['${task.task_id}'] = BashOperator(
${indent}    task_id='${task.task_id}',
${indent}    bash_command='cd /opt/dbt && dbt run',
${indent}    execution_timeout=timedelta(minutes=${task.timeout_minutes}),
${indent})`

      case 'dbt_test':
        return `${indent}tasks['${task.task_id}'] = BashOperator(
${indent}    task_id='${task.task_id}',
${indent}    bash_command='cd /opt/dbt && dbt test',
${indent}    execution_timeout=timedelta(minutes=${task.timeout_minutes}),
${indent})`

      case 'email':
        return `${indent}tasks['${task.task_id}'] = EmailOperator(
${indent}    task_id='${task.task_id}',
${indent}    to='${config.to || 'admin@example.com'}',
${indent}    subject='${config.subject || 'DAG Notification'}',
${indent}    html_content='${config.html_content || 'DAG task completed.'}',
${indent})`

      case 'http_sensor':
        return `${indent}tasks['${task.task_id}'] = HttpSensor(
${indent}    task_id='${task.task_id}',
${indent}    http_conn_id='${config.http_conn_id || 'http_default'}',
${indent}    endpoint='${config.endpoint || '/health'}',
${indent}    poke_interval=60,
${indent}    timeout=${task.timeout_minutes * 60},
${indent})`

      case 'bash_operator':
        return `${indent}tasks['${task.task_id}'] = BashOperator(
${indent}    task_id='${task.task_id}',
${indent}    bash_command='${config.bash_command || 'echo "Hello World"'}',
${indent}    execution_timeout=timedelta(minutes=${task.timeout_minutes}),
${indent})`

      default:
        return `${indent}# Unknown task type: ${task.task_type}`
    }
  }

  const generateDependencyCode = (tasks: TaskConfig[]): string => {
    const lines: string[] = []
    
    // Find root tasks (no dependencies)
    const rootTasks = tasks.filter(t => t.depends_on.length === 0)
    const leafTasks = tasks.filter(t => {
      // A task is a leaf if no other task depends on it
      return !tasks.some(other => other.depends_on.includes(t.task_id))
    })
    
    // Connect start to root tasks
    if (rootTasks.length > 0) {
      lines.push(`start >> [${rootTasks.map(t => `tasks['${t.task_id}']`).join(', ')}]`)
    }
    
    // Add explicit dependencies
    tasks.forEach(task => {
      if (task.depends_on.length > 0) {
        task.depends_on.forEach(dep => {
          lines.push(`tasks['${dep}'] >> tasks['${task.task_id}']`)
        })
      }
    })
    
    // Connect leaf tasks to end
    if (leafTasks.length > 0) {
      lines.push(`[${leafTasks.map(t => `tasks['${t.task_id}']`).join(', ')}] >> end`)
    }
    
    return lines.join('\n')
  }

  // Handle Save with Preview
  const handleSaveWithPreview = async () => {
    const validation = validateDag()
    setValidationResult(validation)
    
    if (!validation.valid) {
      toast({
        title: 'Validation Failed',
        description: validation.errors[0],
        variant: 'destructive',
      })
      return
    }
    
    const code = generateDagCode()
    setPreviewCode(code)
    setShowPreview(true)
  }

  // Confirm save and deploy
  const handleConfirmSave = async () => {
    setIsSaving(true)
    try {
      const tasks = nodesToTasks()
      
      const dagData = {
        dag_id: dagName,
        description,
        schedule_type: cronExpression ? 'cron' as const : 'manual' as const,
        schedule_cron: cronExpression || undefined,
        timezone,
        tags: dagTags,
        tasks,
      }

      let dagIdToUse = dagId
      let wasUpdated = false

      if (isEditing && dagId) {
        // Editing mode - use update
        await dagService.update(dagId, dagData)
        dagIdToUse = dagId
        wasUpdated = true
      } else {
        // Creating mode - but first check if DAG with same name already exists
        try {
          const existingDag = await dagService.get(dagName)
          if (existingDag) {
            // DAG already exists, update it instead
            await dagService.update(existingDag.id, dagData)
            dagIdToUse = existingDag.id
            wasUpdated = true
          }
        } catch {
          // DAG doesn't exist (404), create a new one
          const dag = await dagService.create(dagData)
          dagIdToUse = dag.id
        }
      }

      // Deploy after create/update
      await dagService.deploy(dagIdToUse!)
      
      if (wasUpdated) {
        toast({
          title: 'DAG Updated & Deployed',
          description: `Successfully updated and deployed ${dagName} to Airflow`,
        })
      } else {
        toast({
          title: 'DAG Created & Deployed',
          description: `Successfully created and deployed ${dagName} to Airflow`,
        })
      }
      
      // Navigate to edit mode if we weren't already
      if (!isEditing && dagIdToUse) {
        navigate(`/app/dags/${dagIdToUse}/edit`)
      }
      
      setShowPreview(false)
    } catch (error) {
      console.error('Save error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      toast({
        title: 'Error',
        description: `Failed to save DAG: ${errorMessage}`,
        variant: 'destructive',
      })
    } finally {
      setIsSaving(false)
    }
  }

  // Trigger DAG run
  const handleTriggerRun = async () => {
    if (!dagId && !isEditing) {
      toast({
        title: 'Save Required',
        description: 'Please save the DAG before triggering a run',
        variant: 'destructive',
      })
      return
    }

    setIsTriggering(true)
    try {
      const run = await dagService.trigger(dagId || dagName)
      toast({
        title: 'DAG Triggered',
        description: `Run ${run.run_id} started successfully`,
      })
    } catch (error) {
      console.error('Trigger error:', error)
      toast({
        title: 'Trigger Failed',
        description: 'Failed to trigger DAG run. Make sure it is deployed to Airflow.',
        variant: 'destructive',
      })
    } finally {
      setIsTriggering(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Task Palette */}
      <Card className="w-64 shrink-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Task Types</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {taskTypes.map((task) => (
            <div
              key={task.type}
              draggable
              onDragStart={(e) => onDragStart(e, task.type)}
              className="flex items-center gap-2 rounded-lg border p-2 cursor-grab hover:bg-accent transition-colors"
              style={{ borderLeftColor: task.color, borderLeftWidth: 3 }}
            >
              <task.icon className="h-4 w-4" style={{ color: task.color }} />
              <span className="text-sm">{task.label}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/app/dags')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <span className="text-sm text-muted-foreground">
              {isEditing ? 'Edit DAG' : 'Create New DAG'}
            </span>
            <div className="flex items-center gap-2">
              <Input
                placeholder="dag_name"
                value={dagName}
                onChange={(e) => setDagName(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                className="w-48 font-mono"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleSaveWithPreview} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              Preview & Save
            </Button>
            <Button 
              onClick={handleTriggerRun} 
              disabled={isTriggering || (!isEditing && nodes.length === 0)}
            >
              {isTriggering ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Trigger Run
            </Button>
          </div>
        </div>

        {/* ReactFlow Canvas */}
        <div
          className="flex-1 rounded-lg border bg-background"
          onDrop={onDrop}
          onDragOver={onDragOver}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            fitView
          >
            <Controls />
            <Background />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>

      {/* Properties Panel */}
      <Card className="w-80 shrink-0 overflow-y-auto">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center justify-between">
            {selectedNode ? 'Task Properties' : 'DAG Properties'}
            {selectedNode && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                onClick={() => deleteTask(selectedNode.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedNode ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Task ID</Label>
                <Input value={selectedNode.id} disabled className="font-mono text-xs" />
              </div>
              <div className="space-y-2">
                <Label>Task Type</Label>
                <Input value={selectedNode.data.taskType} disabled />
              </div>
              
              {/* Spark Submit specific config */}
              {selectedNode.data.taskType === 'spark_submit' && (
                <div className="space-y-4 border-t pt-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-primary">
                    <Sparkles className="h-4 w-4" />
                    PySpark App Configuration
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Select PySpark App</Label>
                    {loadingApps ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading apps...
                      </div>
                    ) : (
                      <Select
                        value={taskConfigs[selectedNode.id]?.pyspark_app_id as string || ''}
                        onValueChange={(value) => updateTaskConfig(selectedNode.id, 'pyspark_app_id', value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select a PySpark app..." />
                        </SelectTrigger>
                        <SelectContent>
                          {pysparkApps.length === 0 ? (
                            <div className="px-2 py-1.5 text-sm text-muted-foreground">
                              No PySpark apps available
                            </div>
                          ) : (
                            pysparkApps.map(app => (
                              <SelectItem key={app.id} value={app.id}>
                                {app.name}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                  
                  {/* Show selected app info */}
                  {taskConfigs[selectedNode.id]?.pyspark_app_id && (
                    <div className="rounded-md border p-3 bg-muted/50 text-xs space-y-1">
                      {(() => {
                        const app = pysparkApps.find(a => a.id === taskConfigs[selectedNode.id]?.pyspark_app_id)
                        return app ? (
                          <>
                            <p><strong>App:</strong> {app.name}</p>
                            <p><strong>Table:</strong> {app.source_table}</p>
                            <p><strong>Target:</strong> {app.target_database}.{app.target_table}</p>
                          </>
                        ) : null
                      })()}
                    </div>
                  )}
                  
                  {/* Application Path and Spark Master */}
                  <div className="space-y-2">
                    <Label>Application Path</Label>
                    <Input 
                      placeholder="/opt/spark/jobs/my_job.py"
                      value={taskConfigs[selectedNode.id]?.application_path as string || ''}
                      onChange={(e) => updateTaskConfig(selectedNode.id, 'application_path', e.target.value)}
                      className="font-mono text-xs"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Spark Master</Label>
                    <Input 
                      placeholder="spark://spark-master:7077"
                      value={taskConfigs[selectedNode.id]?.spark_master as string || defaultSparkMaster}
                      onChange={(e) => updateTaskConfig(selectedNode.id, 'spark_master', e.target.value)}
                      className="font-mono text-xs"
                    />
                  </div>
                </div>
              )}
              
              <div className="space-y-2">
                <Label>Timeout (minutes)</Label>
                <Input 
                  type="number" 
                  value={taskConfigs[selectedNode.id]?.timeout_minutes as number || 60}
                  onChange={(e) => updateTaskConfig(selectedNode.id, 'timeout_minutes', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label>Retries</Label>
                <Input 
                  type="number" 
                  value={taskConfigs[selectedNode.id]?.retries as number || 1}
                  onChange={(e) => updateTaskConfig(selectedNode.id, 'retries', parseInt(e.target.value))}
                />
              </div>
              
              {/* Delete task button at bottom */}
              <Button
                variant="destructive"
                size="sm"
                className="w-full mt-4"
                onClick={() => deleteTask(selectedNode.id)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Remove Task
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  placeholder="DAG description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              
              {/* Cron Builder */}
              <div className="border-t pt-4">
                <CronBuilder value={cronExpression} onChange={setCronExpression} />
              </div>
              
              <div className="space-y-2">
                <Label>Timezone</Label>
                <Select value={timezone} onValueChange={setTimezone}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="UTC">UTC</SelectItem>
                    <SelectItem value="America/New_York">America/New_York</SelectItem>
                    <SelectItem value="America/Los_Angeles">America/Los_Angeles</SelectItem>
                    <SelectItem value="Europe/London">Europe/London</SelectItem>
                    <SelectItem value="Europe/Paris">Europe/Paris</SelectItem>
                    <SelectItem value="Asia/Tokyo">Asia/Tokyo</SelectItem>
                    <SelectItem value="Asia/Shanghai">Asia/Shanghai</SelectItem>
                    <SelectItem value="Asia/Riyadh">Asia/Riyadh</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Tag className="h-4 w-4" />
                  <Label>Tags</Label>
                </div>
                <div className="flex flex-wrap gap-1">
                  {dagTags.map(tag => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {dagTags.length === 0 && (
                    <span className="text-xs text-muted-foreground">No tags</span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Auto-tagged with tenant: {tenantName}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Code Preview Dialog */}
      <DagCodePreview
        open={showPreview}
        onOpenChange={setShowPreview}
        dagName={dagName}
        code={previewCode}
        validation={validationResult}
        onConfirmSave={handleConfirmSave}
        isSaving={isSaving}
      />
    </div>
  )
}
