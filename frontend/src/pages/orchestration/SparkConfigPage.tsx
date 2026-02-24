/**
 * NovaSight Spark Configuration Page
 * ====================================
 *
 * Page for configuring remote Spark cluster connection settings
 * including SSH credentials and Spark resource allocation.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobService } from '@/services/jobService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  ArrowLeft,
  Save,
  Loader2,
  Server,
  Key,
  Cpu,
  HardDrive,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
} from 'lucide-react'
import { toast } from '@/components/ui/use-toast'

export function SparkConfigPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Form state
  const [sparkMaster, setSparkMaster] = useState('')
  const [sshHost, setSshHost] = useState('')
  const [sshUser, setSshUser] = useState('spark')
  const [webuiPort, setWebuiPort] = useState(8080)
  const [driverMemory, setDriverMemory] = useState('2g')
  const [executorMemory, setExecutorMemory] = useState('2g')
  const [executorCores, setExecutorCores] = useState(2)
  const [numExecutors, setNumExecutors] = useState(2)
  const [additionalConfigs, setAdditionalConfigs] = useState('')

  // Fetch current config
  const { data: config, isLoading } = useQuery({
    queryKey: ['spark-config'],
    queryFn: () => jobService.getSparkConfig(),
  })

  // Populate form when config loads
  useEffect(() => {
    if (config) {
      setSparkMaster(config.spark_master)
      setSshHost(config.ssh_host || '')
      setSshUser(config.ssh_user || 'spark')
      setWebuiPort(config.webui_port || 8080)
      setDriverMemory(config.driver_memory)
      setExecutorMemory(config.executor_memory)
      setExecutorCores(config.executor_cores)
      setNumExecutors(config.num_executors)
      if (config.additional_configs) {
        setAdditionalConfigs(
          Object.entries(config.additional_configs)
            .map(([k, v]) => `${k}=${v}`)
            .join('\n')
        )
      }
    }
  }, [config])

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: () => {
      // Parse additional configs
      const additionalConfigsObj: Record<string, string> = {}
      additionalConfigs.split('\n').forEach((line) => {
        const [key, ...rest] = line.split('=')
        if (key?.trim() && rest.length > 0) {
          additionalConfigsObj[key.trim()] = rest.join('=').trim()
        }
      })

      return jobService.updateSparkConfig({
        spark_master: sparkMaster,
        ssh_host: sshHost,
        ssh_user: sshUser,
        webui_port: webuiPort,
        driver_memory: driverMemory,
        executor_memory: executorMemory,
        executor_cores: executorCores,
        num_executors: numExecutors,
        additional_configs: additionalConfigsObj,
      })
    },
    onSuccess: () => {
      toast({
        title: 'Configuration Saved',
        description: 'Spark cluster configuration has been updated.',
      })
      queryClient.invalidateQueries({ queryKey: ['spark-config'] })
    },
    onError: (err: Error) => {
      toast({
        title: 'Error',
        description: err.message,
        variant: 'destructive',
      })
    },
  })

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: () => jobService.testSparkConnection({
      spark_master: sparkMaster,
      ssh_host: sshHost,
      ssh_user: sshUser,
      webui_port: webuiPort,
    }),
    onSuccess: (result) => {
      if (result.success) {
        toast({
          title: 'Connection Successful',
          description: 'Successfully connected to Spark cluster.',
        })
      } else {
        toast({
          title: 'Connection Failed',
          description: result.errors.join(', ') || 'Could not connect to Spark cluster',
          variant: 'destructive',
        })
      }
    },
    onError: (err: Error) => {
      toast({
        title: 'Test Failed',
        description: err.message,
        variant: 'destructive',
      })
    },
  })

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Spark Cluster Configuration</h1>
          <p className="text-muted-foreground">
            Configure connection settings for remote Spark execution
          </p>
        </div>
      </div>

      {/* Connection Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Connection Status</CardTitle>
              <CardDescription>
                Test connectivity to your Spark cluster
              </CardDescription>
            </div>
            <Button
              variant="outline"
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
            >
              {testMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Test Connection
            </Button>
          </div>
        </CardHeader>
        {testMutation.data && (
          <CardContent>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                {testMutation.data.ssh_connection === null ? (
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                ) : testMutation.data.ssh_connection ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
                <span className="text-sm">
                  SSH: {testMutation.data.ssh_connection === null ? 'Not configured' : testMutation.data.ssh_connection ? 'Connected' : 'Failed'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {testMutation.data.spark_master ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
                <span className="text-sm">
                  Spark Master: {testMutation.data.spark_master ? 'Available' : 'Unavailable'}
                </span>
              </div>
            </div>
            {testMutation.data.errors.length > 0 && (
              <div className="mt-3 p-3 bg-red-50 rounded-lg">
                <p className="text-sm text-red-700 font-medium">Errors:</p>
                <ul className="text-sm text-red-600 mt-1">
                  {testMutation.data.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Spark Master Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Server className="h-5 w-5" />
            Spark Master
          </CardTitle>
          <CardDescription>
            Connection settings for your Spark cluster master
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="sparkMaster">Spark Master URL</Label>
            <Input
              id="sparkMaster"
              value={sparkMaster}
              onChange={(e) => setSparkMaster(e.target.value)}
              placeholder="spark://spark-master:7077"
            />
            <p className="text-xs text-muted-foreground">
              Examples: spark://host:7077, yarn, k8s://https://kubernetes
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="webuiPort">Spark Master Web UI Port</Label>
            <Input
              id="webuiPort"
              type="number"
              min={1}
              max={65535}
              value={webuiPort}
              onChange={(e) => setWebuiPort(parseInt(e.target.value) || 8080)}
              placeholder="8080"
            />
            <p className="text-xs text-muted-foreground">
              The port used by Spark Master's REST API for connection testing (default: 8080)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* SSH Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Key className="h-5 w-5" />
            SSH Configuration
          </CardTitle>
          <CardDescription>
            SSH credentials for remote spark-submit execution (optional)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="sshHost">SSH Host</Label>
              <Input
                id="sshHost"
                value={sshHost}
                onChange={(e) => setSshHost(e.target.value)}
                placeholder="spark-master.example.com"
              />
              <p className="text-xs text-muted-foreground">
                Leave empty for local execution
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="sshUser">SSH User</Label>
              <Input
                id="sshUser"
                value={sshUser}
                onChange={(e) => setSshUser(e.target.value)}
                placeholder="spark"
              />
            </div>
          </div>
          <div className="p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground">
              <strong>Note:</strong> SSH key authentication is configured at the server level.
              Ensure the Dagster worker has SSH key access to the Spark master node.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Resource Allocation */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Resource Allocation
          </CardTitle>
          <CardDescription>
            Default resource settings for Spark jobs
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
            </div>
            <div className="space-y-2">
              <Label htmlFor="executorMemory">Executor Memory</Label>
              <Input
                id="executorMemory"
                value={executorMemory}
                onChange={(e) => setExecutorMemory(e.target.value)}
                placeholder="2g"
              />
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
            <HardDrive className="h-5 w-5" />
            Advanced Configuration
          </CardTitle>
          <CardDescription>
            Additional Spark configuration properties
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="additionalConfigs">Additional Spark Configs</Label>
            <textarea
              id="additionalConfigs"
              className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
              value={additionalConfigs}
              onChange={(e) => setAdditionalConfigs(e.target.value)}
              placeholder="spark.sql.adaptive.enabled=true
spark.sql.shuffle.partitions=200"
            />
            <p className="text-xs text-muted-foreground">
              One config per line in format: key=value
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
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Configuration
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

export default SparkConfigPage
