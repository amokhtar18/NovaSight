import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, CheckCircle2, XCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { DataSourceTypeSelector } from './DataSourceTypeSelector'
import { ConnectionForm } from './ConnectionForm'
import { SchemaSelector } from './SchemaSelector'
import { FileUploadStep } from './FileUploadStep'
import { useTestNewConnection, useCreateDataSource } from '../hooks'
import type { DatabaseType, ConnectionTestResult, FileUploadMetadata } from '@/types/datasource'
import { DATABASE_TYPES, isFileBased } from '@/types/datasource'

const DB_STEPS = [
  { id: 'type', title: 'Select Type', description: 'Choose your data source' },
  { id: 'connection', title: 'Connection Details', description: 'Enter connection information' },
  { id: 'test', title: 'Test Connection', description: 'Verify the connection works' },
  { id: 'schema', title: 'Select Schema', description: 'Choose the database schema' },
]

const FILE_STEPS = [
  { id: 'type', title: 'Select Type', description: 'Choose your data source' },
  { id: 'upload', title: 'Upload File', description: 'Upload and validate your file' },
  { id: 'name', title: 'Name & Save', description: 'Give your connection a name' },
]

  const connectionSchema = z.object({
    name: z.string().min(1, 'Name is required').max(100),
    db_type: z.enum(['postgresql', 'mysql', 'oracle', 'sqlserver', 'mongodb', 'clickhouse', 'flatfile', 'excel', 'sqlite'] as const),
    host: z.string().optional(),
    port: z.number().optional(),
    database: z.string().optional(),
    username: z.string().optional(),
    password: z.string().optional(),
    ssl_enabled: z.boolean().default(true),
    service_name: z.string().optional(),
    thick_mode: z.boolean().default(false),
  })

interface ConnectionWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function ConnectionWizard({ open, onOpenChange, onSuccess }: ConnectionWizardProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [selectedType, setSelectedType] = useState<DatabaseType | null>(null)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [selectedSchemas, setSelectedSchemas] = useState<string[]>([])
  const [uploadedMeta, setUploadedMeta] = useState<FileUploadMetadata | null>(null)
  const [connectionName, setConnectionName] = useState('')

  const fileMode = selectedType ? isFileBased(selectedType) : false
  const steps = fileMode ? FILE_STEPS : DB_STEPS

  const testConnection = useTestNewConnection()
  const createDataSource = useCreateDataSource()

  const form = useForm<ConnectionFormData>({
    resolver: zodResolver(connectionSchema),
    defaultValues: {
      ssl_enabled: true,
      port: 5432,
      thick_mode: false,
      service_name: '',
    },
  })

  const handleTypeSelect = (type: DatabaseType) => {
    setSelectedType(type)
    form.setValue('db_type', type)

    if (!isFileBased(type)) {
      // Set default port based on type
      const defaultPorts: Partial<Record<DatabaseType, number>> = {
        postgresql: 5432,
        mysql: 3306,
        oracle: 1521,
        sqlserver: 1433,
        mongodb: 27017,
        clickhouse: 9000,
      }
      form.setValue('port', defaultPorts[type] ?? 5432)
    }

    setCurrentStep(1)
  }

  // Build extra_params for database-specific options
  const buildExtraParams = (data: ConnectionFormData) => {
    const extra: Record<string, unknown> = {}
    
    // Oracle-specific options
    if (data.db_type === 'oracle') {
      if (data.thick_mode) extra.thick_mode = true
      if (data.service_name) extra.service_name = data.service_name
    }
    
    return Object.keys(extra).length > 0 ? extra : undefined
  }

  const handleConnectionSubmit = async (data: ConnectionFormData) => {
    setTestResult(null)
    setCurrentStep(2) // Move to test step to show loading/result
    try {
      // Include extra_params when testing connection
      const testData = {
        ...data,
        extra_params: buildExtraParams(data),
      }
      const result = await testConnection.mutateAsync(testData)
      setTestResult(result)
      if (result.success) {
        // Move to schema selection step
        setCurrentStep(3)
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection failed',
      })
    }
  }

  const handleFinish = async () => {
    const data = form.getValues()
    try {
      if (fileMode && uploadedMeta) {
        // File-based source: send upload_token + optional overrides
        const name = connectionName.trim() || uploadedMeta.file_name
        await createDataSource.mutateAsync({
          name,
          db_type: selectedType!,
          upload_token: uploadedMeta.upload_token,
          extra_params: {
            file_name: uploadedMeta.file_name,
            file_size: uploadedMeta.file_size,
            file_format: uploadedMeta.file_format,
            file_hash: uploadedMeta.file_hash,
          },
        })
      } else {
        const extraParams = buildExtraParams(data) || {}
        if (selectedSchemas.length > 0) {
          extraParams.allowed_schemas = selectedSchemas
        }
        await createDataSource.mutateAsync({
          ...data,
          schema_name: selectedSchemas[0] || undefined,
          extra_params: Object.keys(extraParams).length > 0 ? extraParams : undefined,
        })
      }
      handleClose()
      onSuccess?.()
    } catch (error) {
      // Error is handled by the mutation
    }
  }

  const handleClose = () => {
    setCurrentStep(0)
    setSelectedType(null)
    setTestResult(null)
    setSelectedSchemas([])
    setUploadedMeta(null)
    setConnectionName('')
    form.reset()
    onOpenChange(false)
  }

  const canGoNext = () => {
    if (fileMode) {
      switch (currentStep) {
        case 0: return selectedType !== null
        case 1: return uploadedMeta !== null
        case 2: return (connectionName.trim() || uploadedMeta?.file_name || '').length > 0
        default: return true
      }
    }
    switch (currentStep) {
      case 0:
        return selectedType !== null
      case 1:
        return form.formState.isValid
      case 2:
        return testResult?.success
      case 3:
        return selectedSchemas.length > 0
      default:
        return true
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Connect Data Source</DialogTitle>
          <DialogDescription>
            Follow the steps to connect your database
          </DialogDescription>
        </DialogHeader>

        {/* Stepper */}
        <div className="flex items-center justify-between px-4 py-6">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors",
                    index < currentStep
                      ? "bg-primary border-primary text-primary-foreground"
                      : index === currentStep
                      ? "border-primary text-primary"
                      : "border-muted text-muted-foreground"
                  )}
                >
                  {index < currentStep ? (
                    <CheckCircle2 className="h-5 w-5" />
                  ) : (
                    <span className="text-sm font-medium">{index + 1}</span>
                  )}
                </div>
                <div className="mt-2 text-center">
                  <p className="text-sm font-medium">{step.title}</p>
                  <p className="text-xs text-muted-foreground hidden sm:block">{step.description}</p>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "h-[2px] w-12 mx-4 transition-colors",
                    index < currentStep ? "bg-primary" : "bg-muted"
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="min-h-[300px]">
          {currentStep === 0 && (
            <DataSourceTypeSelector
              selected={selectedType}
              onSelect={handleTypeSelect}
            />
          )}

          {fileMode ? (
            <>
              {currentStep === 1 && selectedType && (
                <FileUploadStep
                  dbType={selectedType}
                  uploadedMeta={uploadedMeta}
                  onUploadComplete={setUploadedMeta}
                />
              )}
              {currentStep === 2 && uploadedMeta && (
                <FileNameStep
                  defaultName={uploadedMeta.file_name}
                  value={connectionName}
                  onChange={setConnectionName}
                />
              )}
            </>
          ) : (
            <>
              {currentStep === 1 && (
                <ConnectionForm form={form} onSubmit={handleConnectionSubmit} />
              )}

              {currentStep === 2 && (
                <TestConnectionStep
                  isLoading={testConnection.isPending}
                  result={testResult}
                  onRetry={() => handleConnectionSubmit(form.getValues())}
                />
              )}

              {currentStep === 3 && (
                <SchemaSelector
                  connectionData={form.getValues()}
                  testResult={testResult}
                  selectedSchemas={selectedSchemas}
                  onSchemasChange={setSelectedSchemas}
                />
              )}
            </>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back
          </Button>

          {currentStep < steps.length - 1 ? (
            <Button
              onClick={() => {
                if (!fileMode && currentStep === 1) {
                  form.handleSubmit(handleConnectionSubmit)()
                } else {
                  setCurrentStep(currentStep + 1)
                }
              }}
              disabled={!canGoNext() || testConnection.isPending}
            >
              {testConnection.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  {!fileMode && currentStep === 1 ? 'Test Connection' : 'Next'}
                  <ChevronRight className="h-4 w-4 ml-1" />
                </>
              )}
            </Button>
          ) : (
            <Button
              onClick={handleFinish}
              disabled={!canGoNext() || createDataSource.isPending}
            >
              {createDataSource.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Connection'
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface TestConnectionStepProps {
  isLoading: boolean
  result: ConnectionTestResult | null
  onRetry: () => void
}

function TestConnectionStep({ isLoading, result, onRetry }: TestConnectionStepProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <p className="text-lg font-medium">Testing connection...</p>
        <p className="text-sm text-muted-foreground">This may take a few seconds</p>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <p>Waiting to test connection...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 space-y-6">
      {result.success ? (
        <>
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
            <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
          </div>
          <div className="text-center space-y-2">
            <h3 className="text-xl font-semibold text-green-600 dark:text-green-400">
              Connection Successful!
            </h3>
            <p className="text-muted-foreground">{result.message}</p>
          </div>
          {result.details && (
            <div className="w-full max-w-md p-4 border rounded-lg bg-muted/50 space-y-2">
              {result.details.version && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Version:</span>
                  <span className="font-mono">{result.details.version}</span>
                </div>
              )}
              {result.details.schemas && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Schemas:</span>
                  <span className="font-mono">{result.details.schemas.length}</span>
                </div>
              )}
              {result.details.latency_ms && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Latency:</span>
                  <span className="font-mono">{result.details.latency_ms}ms</span>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <>
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
            <XCircle className="h-12 w-12 text-red-600 dark:text-red-400" />
          </div>
          <div className="text-center space-y-2">
            <h3 className="text-xl font-semibold text-red-600 dark:text-red-400">
              Connection Failed
            </h3>
            <p className="text-muted-foreground">{result.message}</p>
          </div>
          <Button onClick={onRetry} variant="outline">
            Retry Connection
          </Button>
        </>
      )}
    </div>
  )
}

interface FileNameStepProps {
  defaultName: string
  value: string
  onChange: (v: string) => void
}

function FileNameStep({ defaultName, value, onChange }: FileNameStepProps) {
  return (
    <div className="space-y-4 py-6">
      <div>
        <h3 className="text-lg font-medium mb-1">Name this connection</h3>
        <p className="text-sm text-muted-foreground">
          Choose a friendly name for this data source. Defaults to the uploaded file name.
        </p>
      </div>
      <div>
        <label htmlFor="conn-name" className="text-sm font-medium">
          Connection Name
        </label>
        <input
          id="conn-name"
          type="text"
          value={value}
          placeholder={defaultName}
          onChange={(e) => onChange(e.target.value)}
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          maxLength={100}
        />
      </div>
    </div>
  )
}
