import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, Database, CheckCircle, XCircle } from 'lucide-react'

export function ConnectionsPage() {
  // Placeholder data
  const connections = [
    {
      id: '1',
      name: 'Production PostgreSQL',
      db_type: 'postgresql',
      host: 'prod-db.example.com',
      status: 'active',
      last_tested: '2024-01-15T10:30:00Z',
      test_result: true,
    },
    {
      id: '2',
      name: 'Analytics Oracle',
      db_type: 'oracle',
      host: 'oracle.example.com',
      status: 'active',
      last_tested: '2024-01-14T14:20:00Z',
      test_result: true,
    },
    {
      id: '3',
      name: 'Legacy SQL Server',
      db_type: 'sqlserver',
      host: 'sqlserver.example.com',
      status: 'inactive',
      last_tested: '2024-01-10T09:00:00Z',
      test_result: false,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Data Connections</h1>
          <p className="text-muted-foreground">
            Manage connections to your data sources
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Connection
        </Button>
      </div>

      {/* Connections Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {connections.map((conn) => (
          <Card key={conn.id} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">{conn.name}</CardTitle>
                </div>
                {conn.test_result ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type:</span>
                  <span className="font-medium uppercase">{conn.db_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Host:</span>
                  <span className="font-medium">{conn.host}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span
                    className={`font-medium ${
                      conn.status === 'active'
                        ? 'text-green-600'
                        : 'text-gray-500'
                    }`}
                  >
                    {conn.status}
                  </span>
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                <Button variant="outline" size="sm">
                  Test
                </Button>
                <Button variant="outline" size="sm">
                  Edit
                </Button>
                <Button variant="outline" size="sm">
                  Browse
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
