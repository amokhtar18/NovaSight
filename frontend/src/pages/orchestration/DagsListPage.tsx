import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { dagService, DagConfig } from '@/services/dagService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Plus,
  Play,
  Pause,
  Eye,
  Settings,
  Loader2,
  GitBranch,
} from 'lucide-react'
import { formatDate } from '@/lib/utils'

export function DagsListPage() {
  const {
    data: dags,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['dags'],
    queryFn: () => dagService.list(),
  })

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      active: 'bg-green-100 text-green-800',
      paused: 'bg-yellow-100 text-yellow-800',
      archived: 'bg-red-100 text-red-800',
    }
    return (
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
          styles[status] || styles.draft
        }`}
      >
        {status}
      </span>
    )
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
      <div className="flex h-64 items-center justify-center">
        <p className="text-destructive">Failed to load DAGs</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">DAG Workflows</h1>
          <p className="text-muted-foreground">
            Manage your data pipeline orchestration
          </p>
        </div>
        <Button asChild>
          <Link to="/dags/new">
            <Plus className="mr-2 h-4 w-4" />
            Create DAG
          </Link>
        </Button>
      </div>

      {/* DAGs Grid */}
      {dags && dags.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {dags.map((dag: DagConfig) => (
            <Card key={dag.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{dag.dag_id}</CardTitle>
                  {getStatusBadge(dag.status)}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                  {dag.description || 'No description'}
                </p>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Schedule:</span>
                    <span className="font-medium">
                      {dag.schedule_type === 'cron'
                        ? dag.schedule_cron
                        : dag.schedule_type === 'preset'
                        ? dag.schedule_preset
                        : 'Manual'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Version:</span>
                    <span className="font-medium">v{dag.current_version}</span>
                  </div>
                  {dag.deployed_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Last deployed:</span>
                      <span className="font-medium">{formatDate(dag.deployed_at)}</span>
                    </div>
                  )}
                </div>

                <div className="mt-4 flex gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <Link to={`/dags/${dag.id}/edit`}>
                      <Settings className="mr-1 h-3 w-3" />
                      Edit
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <Link to={`/dags/${dag.id}/monitor`}>
                      <Eye className="mr-1 h-3 w-3" />
                      Monitor
                    </Link>
                  </Button>
                  {dag.status === 'active' ? (
                    <Button variant="outline" size="sm">
                      <Pause className="mr-1 h-3 w-3" />
                      Pause
                    </Button>
                  ) : dag.status === 'paused' ? (
                    <Button variant="outline" size="sm">
                      <Play className="mr-1 h-3 w-3" />
                      Resume
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <GitBranch className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No DAGs yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first workflow to start orchestrating data pipelines.
            </p>
            <Button asChild>
              <Link to="/dags/new">
                <Plus className="mr-2 h-4 w-4" />
                Create Your First DAG
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
