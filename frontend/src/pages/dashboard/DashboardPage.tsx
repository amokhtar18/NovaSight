import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import {
  Database,
  GitBranch,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
} from 'lucide-react'

export function DashboardPage() {
  const { user } = useAuth()

  const stats = [
    {
      title: 'Data Connections',
      value: '8',
      change: '+2 this month',
      icon: Database,
      color: 'text-blue-500',
    },
    {
      title: 'Active DAGs',
      value: '12',
      change: '3 running now',
      icon: GitBranch,
      color: 'text-green-500',
    },
    {
      title: 'Jobs Today',
      value: '47',
      change: '95% success rate',
      icon: Activity,
      color: 'text-purple-500',
    },
    {
      title: 'Alerts',
      value: '2',
      change: '1 critical',
      icon: AlertTriangle,
      color: 'text-orange-500',
    },
  ]

  const recentRuns = [
    {
      dagId: 'sales_ingestion_daily',
      status: 'success',
      duration: '12m 34s',
      completedAt: '10 minutes ago',
    },
    {
      dagId: 'customer_sync',
      status: 'running',
      duration: '5m 22s',
      completedAt: 'In progress',
    },
    {
      dagId: 'inventory_refresh',
      status: 'success',
      duration: '8m 12s',
      completedAt: '1 hour ago',
    },
    {
      dagId: 'analytics_rollup',
      status: 'failed',
      duration: '3m 45s',
      completedAt: '2 hours ago',
    },
    {
      dagId: 'dbt_daily_transform',
      status: 'success',
      duration: '25m 18s',
      completedAt: '3 hours ago',
    },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />
      case 'failed':
        return <AlertTriangle className="h-4 w-4 text-red-500" />
      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back, {user?.name}. Here's what's happening with your data platform.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">{stat.change}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Runs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent DAG Runs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentRuns.map((run, index) => (
              <div
                key={index}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(run.status)}
                  <div>
                    <p className="font-medium">{run.dagId}</p>
                    <p className="text-sm text-muted-foreground">
                      Duration: {run.duration}
                    </p>
                  </div>
                </div>
                <div className="text-right text-sm text-muted-foreground">
                  {run.completedAt}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
