import {
  Database,
  MoreVertical,
  Play,
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { DataSource } from '@/types/datasource'
import { DATABASE_TYPES } from '@/types/datasource'
import { formatDistanceToNow } from 'date-fns'
import { useNavigate } from 'react-router-dom'
import { useTestConnection, useDeleteDataSource, useTriggerSync } from '../hooks'

interface DataSourceCardProps {
  datasource: DataSource
}

export function DataSourceCard({ datasource }: DataSourceCardProps) {
  const navigate = useNavigate()
  const testConnection = useTestConnection()
  const deleteDataSource = useDeleteDataSource()
  const triggerSync = useTriggerSync()

  const dbTypeInfo = DATABASE_TYPES[datasource.db_type]

  const statusConfig = {
    active: { variant: 'success' as const, icon: CheckCircle2, label: 'Active' },
    inactive: { variant: 'secondary' as const, icon: Clock, label: 'Inactive' },
    testing: { variant: 'info' as const, icon: Clock, label: 'Testing' },
    error: { variant: 'destructive' as const, icon: AlertCircle, label: 'Error' },
  }

  const status = statusConfig[datasource.status]
  const StatusIcon = status.icon

  const handleTest = async (e: React.MouseEvent) => {
    e.stopPropagation()
    testConnection.mutate(datasource.id)
  }

  const handleSync = async (e: React.MouseEvent) => {
    e.stopPropagation()
    triggerSync.mutate({ id: datasource.id })
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm(`Are you sure you want to delete "${datasource.name}"?`)) {
      deleteDataSource.mutate(datasource.id)
    }
  }

  return (
    <Card
      className="group relative overflow-hidden border-border/60 hover:border-primary/40 hover:shadow-md transition-all cursor-pointer"
      onClick={() => navigate(`/app/datasources/${datasource.id}`)}
    >
      {/* Top accent bar — subtle category color */}
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary/60 to-blue-500/60" />

      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3 pt-5">
        <div className="flex items-start gap-3 min-w-0">
          <div className="p-2.5 rounded-lg shrink-0 bg-primary/10 text-primary">
            <Database className="h-5 w-5" />
          </div>
          <div className="space-y-0.5 min-w-0">
            <h3 className="font-semibold text-base leading-tight truncate" title={datasource.name}>
              {datasource.name}
            </h3>
            <p className="text-xs text-muted-foreground">{dbTypeInfo.name}</p>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={handleTest}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Test Connection
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleSync}>
              <Play className="h-4 w-4 mr-2" />
              Trigger Sync
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleDelete} className="text-destructive">
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={status.variant}>
            <StatusIcon className="h-3 w-3 mr-1" />
            {status.label}
          </Badge>
          {datasource.ssl_enabled && <Badge variant="outline">SSL</Badge>}
        </div>

        {/* Type-specific metadata */}
        <dl className="text-xs space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <dt className="text-muted-foreground">Host</dt>
              <dd className="font-mono truncate text-right" title={`${datasource.host ?? ''}:${datasource.port ?? ''}`}>
                {datasource.host ?? '—'}
                {datasource.port ? `:${datasource.port}` : ''}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-2">
              <dt className="text-muted-foreground">Database</dt>
              <dd className="font-mono truncate text-right" title={datasource.database}>
                {datasource.database ?? '—'}
              </dd>
            </div>
            {datasource.schema_name && (
              <div className="flex items-baseline justify-between gap-2">
                <dt className="text-muted-foreground">Schema</dt>
                <dd className="font-mono truncate text-right">{datasource.schema_name}</dd>
              </div>
            )}
          </dl>

        <div className="text-[11px] text-muted-foreground pt-2 border-t border-border/60">
          {datasource.last_synced_at
            ? `Last synced ${formatDistanceToNow(new Date(datasource.last_synced_at), { addSuffix: true })}`
            : `Created ${formatDistanceToNow(new Date(datasource.created_at), { addSuffix: true })}`}
        </div>
      </CardContent>
    </Card>
  )
}
