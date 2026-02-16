import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Database,
  Play,
  RefreshCw,
  Settings,
  Trash2,
  Download,
  AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { SchemaBrowser } from '../components/SchemaBrowser'
import {
  useDataSource,
  useTestConnection,
  useDeleteDataSource,
  useTriggerSync,
} from '../hooks'
import { DATABASE_TYPES } from '@/types/datasource'
import { formatDistanceToNow } from 'date-fns'

export function DataSourceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: datasource, isLoading, error } = useDataSource(id!)
  const testConnection = useTestConnection()
  const deleteDataSource = useDeleteDataSource()
  const triggerSync = useTriggerSync()

  const handleTest = () => {
    if (id) {
      testConnection.mutate(id)
    }
  }

  const handleSync = () => {
    if (id) {
      triggerSync.mutate({ id })
    }
  }

  const handleDelete = () => {
    if (id && confirm(`Are you sure you want to delete "${datasource?.name}"?`)) {
      deleteDataSource.mutate(id, {
        onSuccess: () => navigate('/app/datasources'),
      })
    }
  }

  if (isLoading) {
    return (
      <div className="container py-8 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-6">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[400px]" />
        </div>
      </div>
    )
  }

  if (error || !datasource) {
    return (
      <div className="container py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Failed to load data source. It may have been deleted.
          </AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/app/datasources')} className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Data Sources
        </Button>
      </div>
    )
  }

  const dbTypeInfo = DATABASE_TYPES[datasource.db_type]
  const statusConfig = {
    active: { variant: 'success' as const, label: 'Active' },
    inactive: { variant: 'secondary' as const, label: 'Inactive' },
    testing: { variant: 'info' as const, label: 'Testing' },
    error: { variant: 'destructive' as const, label: 'Error' },
  }
  const status = statusConfig[datasource.status]

  return (
    <div className="container py-8 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/app/datasources')}
            className="mb-2 -ml-2"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Data Sources
          </Button>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-primary/10">
              <Database className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">{datasource.name}</h1>
              <p className="text-muted-foreground">{dbTypeInfo.name}</p>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleTest}
            disabled={testConnection.isPending}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${testConnection.isPending ? 'animate-spin' : ''}`}
            />
            Test Connection
          </Button>
          <Button onClick={handleSync} disabled={triggerSync.isPending}>
            <Play
              className={`h-4 w-4 mr-2 ${triggerSync.isPending ? 'animate-spin' : ''}`}
            />
            Sync Now
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Status</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant={status.variant}>{status.label}</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Database Type</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-semibold">{dbTypeInfo.name}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>SSL/TLS</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant={datasource.ssl_enabled ? 'success' : 'secondary'}>
              {datasource.ssl_enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Last Synced</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm">
              {datasource.last_synced_at
                ? formatDistanceToNow(new Date(datasource.last_synced_at), {
                    addSuffix: true,
                  })
                : 'Never'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="schema">Schema</TabsTrigger>
          <TabsTrigger value="sync">Sync History</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Connection Details</CardTitle>
              <CardDescription>Database connection information</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground mb-1">Host</dt>
                  <dd className="font-mono text-sm">{datasource.host}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground mb-1">Port</dt>
                  <dd className="font-mono text-sm">{datasource.port}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground mb-1">Database</dt>
                  <dd className="font-mono text-sm">{datasource.database}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground mb-1">Allowed Schemas</dt>
                  <dd className="font-mono text-sm">
                    {datasource.extra_params?.allowed_schemas?.length > 0
                      ? (datasource.extra_params.allowed_schemas as string[]).join(', ')
                      : datasource.schema_name || 'All schemas'}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground mb-1">Username</dt>
                  <dd className="font-mono text-sm">{datasource.username}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground mb-1">Created</dt>
                  <dd className="text-sm">
                    {new Date(datasource.created_at).toLocaleString()}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground mb-1">Updated</dt>
                  <dd className="text-sm">
                    {new Date(datasource.updated_at).toLocaleString()}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schema">
          <Card>
            <CardHeader>
              <CardTitle>Database Schema</CardTitle>
              <CardDescription>
                Browse tables and columns in this database
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SchemaBrowser datasourceId={id!} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sync">
          <Card>
            <CardHeader>
              <CardTitle>Sync History</CardTitle>
              <CardDescription>View past synchronization jobs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12 text-muted-foreground">
                <p className="text-sm">Sync history will be displayed here</p>
                <p className="text-xs mt-1">This feature is coming soon</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Connection Settings</CardTitle>
              <CardDescription>Manage connection configuration</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12 text-muted-foreground">
                <p className="text-sm">Settings editor will be displayed here</p>
                <p className="text-xs mt-1">This feature is coming soon</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
