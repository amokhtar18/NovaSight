import { useCallback, useState } from 'react'
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
import {
  Save,
  Play,
  Upload,
  ArrowLeft,
  Database,
  Code2,
  Mail,
  Timer,
  Terminal,
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
  const isEditing = !!dagId

  const [dagName, setDagName] = useState(dagId || '')
  const [description, setDescription] = useState('')
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

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

  const handleSave = async () => {
    // TODO: Implement save logic
    console.log('Saving DAG:', { dagName, description, nodes, edges })
  }

  const handleDeploy = async () => {
    // TODO: Implement deploy logic
    console.log('Deploying DAG')
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
            <Button variant="ghost" size="sm" onClick={() => navigate('/dags')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <span className="text-sm text-muted-foreground">
              {isEditing ? 'Edit DAG' : 'Create New DAG'}
            </span>
            <div className="flex items-center gap-2">
              <Input
                placeholder="DAG Name"
                value={dagName}
                onChange={(e) => setDagName(e.target.value)}
                className="w-48"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleSave}>
              <Save className="mr-2 h-4 w-4" />
              Save
            </Button>
            <Button variant="outline" onClick={handleDeploy}>
              <Upload className="mr-2 h-4 w-4" />
              Deploy
            </Button>
            <Button>
              <Play className="mr-2 h-4 w-4" />
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
            fitView
          >
            <Controls />
            <Background />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>

      {/* Properties Panel */}
      <Card className="w-80 shrink-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            {selectedNode ? 'Task Properties' : 'DAG Properties'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedNode ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Task ID</Label>
                <Input value={selectedNode.id} disabled />
              </div>
              <div className="space-y-2">
                <Label>Task Type</Label>
                <Input value={selectedNode.data.taskType} disabled />
              </div>
              <div className="space-y-2">
                <Label>Timeout (minutes)</Label>
                <Input type="number" defaultValue={60} />
              </div>
              <div className="space-y-2">
                <Label>Retries</Label>
                <Input type="number" defaultValue={1} />
              </div>
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
              <div className="space-y-2">
                <Label>Schedule</Label>
                <Input placeholder="0 0 * * *" />
              </div>
              <div className="space-y-2">
                <Label>Timezone</Label>
                <Input defaultValue="UTC" />
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
