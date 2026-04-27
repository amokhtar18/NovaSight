/**
 * Pipeline Wizard - 4-Step Pipeline Creation
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Check, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useToast } from '@/components/ui/use-toast'
import { SourceSelector } from './SourceSelector'
import { SourceKindStep } from './SourceKindStep'
import { FileSourceSelector } from './FileSourceSelector'
import { ColumnSelector } from './ColumnSelector'
import { TargetConfiguration } from './TargetConfiguration'
import { ReviewStep } from './ReviewStep'
import { useCreatePipeline, useActivatePipeline } from '../hooks'
import type { WizardState, WizardStep, PipelineFormData } from '@/types/pipeline'

const STEPS: { id: WizardStep; title: string; description: string }[] = [
  { id: 'kind', title: 'Type', description: 'Database or file' },
  { id: 'source', title: 'Source', description: 'Select data source' },
  { id: 'columns', title: 'Columns', description: 'Choose columns and keys' },
  { id: 'target', title: 'Target', description: 'Configure write mode' },
  { id: 'review', title: 'Review', description: 'Preview and create' },
]

const INITIAL_STATE: WizardState = {
  currentStep: 'kind',
  isValid: false,
  errors: {},
  name: '',
  description: '',
  sourceKind: 'sql',
  connectionId: '',
  sourceType: 'table',
  sourceSchema: undefined,
  sourceTable: undefined,
  sourceQuery: undefined,
  fileFormat: undefined,
  fileObjectKey: undefined,
  fileOriginalName: undefined,
  fileSizeBytes: undefined,
  fileOptions: {},
  columnsConfig: [],
  primaryKeyColumns: [],
  incrementalCursorColumn: undefined,
  incrementalCursorType: 'none',
  writeDisposition: 'append',
  partitionColumns: [],
  icebergNamespace: undefined,
  icebergTableName: undefined,
  options: {},
}

export function PipelineWizard() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [state, setState] = useState<WizardState>(INITIAL_STATE)
  
  const createPipeline = useCreatePipeline()
  const activatePipeline = useActivatePipeline()

  const currentStepIndex = STEPS.findIndex(s => s.id === state.currentStep)
  const progress = ((currentStepIndex + 1) / STEPS.length) * 100

  const handleStateChange = (updates: Partial<WizardState>) => {
    setState(prev => ({ ...prev, ...updates }))
  }

  const canProceed = (): boolean => {
    switch (state.currentStep) {
      case 'kind':
        return !!state.sourceKind
      case 'source':
        if (state.sourceKind === 'file') {
          if (!state.fileObjectKey || !state.fileFormat) return false
          // Excel requires a chosen sheet
          if (
            (state.fileFormat === 'xlsx' || state.fileFormat === 'xls') &&
            !state.fileOptions?.sheet_name
          ) {
            return false
          }
          return true
        }
        if (!state.connectionId) return false
        if (state.sourceType === 'table' && !state.sourceTable) return false
        if (state.sourceType === 'query' && !state.sourceQuery) return false
        return true
      case 'columns':
        return state.columnsConfig.some(c => c.include)
      case 'target':
        if (!state.name) return false
        if ((state.writeDisposition === 'merge' || state.writeDisposition === 'scd2') &&
            (!state.primaryKeyColumns || state.primaryKeyColumns.length === 0)) {
          return false
        }
        return true
      case 'review':
        return true
      default:
        return false
    }
  }

  const goNext = () => {
    const currentIndex = STEPS.findIndex(s => s.id === state.currentStep)
    if (currentIndex < STEPS.length - 1) {
      setState(prev => ({ ...prev, currentStep: STEPS[currentIndex + 1].id }))
    }
  }

  const goPrev = () => {
    const currentIndex = STEPS.findIndex(s => s.id === state.currentStep)
    if (currentIndex > 0) {
      setState(prev => ({ ...prev, currentStep: STEPS[currentIndex - 1].id }))
    }
  }

  const handleCreate = async () => {
    const isFile = state.sourceKind === 'file'
    const formData: PipelineFormData = {
      name: state.name,
      description: state.description,
      sourceKind: state.sourceKind,
      connectionId: isFile ? undefined : state.connectionId,
      sourceType: state.sourceType,
      sourceSchema: isFile ? undefined : state.sourceSchema,
      sourceTable: isFile ? undefined : state.sourceTable,
      sourceQuery: isFile ? undefined : state.sourceQuery,
      fileFormat: isFile ? state.fileFormat : undefined,
      fileObjectKey: isFile ? state.fileObjectKey : undefined,
      fileOriginalName: isFile ? state.fileOriginalName : undefined,
      fileSizeBytes: isFile ? state.fileSizeBytes : undefined,
      fileOptions: isFile ? (state.fileOptions ?? {}) : {},
      columnsConfig: state.columnsConfig.filter(c => c.include),
      primaryKeyColumns: state.primaryKeyColumns,
      incrementalCursorColumn: state.incrementalCursorColumn,
      incrementalCursorType: state.incrementalCursorType,
      writeDisposition: state.writeDisposition,
      partitionColumns: state.partitionColumns,
      icebergNamespace: state.icebergNamespace,
      icebergTableName: state.icebergTableName,
      options: state.options,
    }

    try {
      const pipeline = await createPipeline.mutateAsync(formData)
      // Auto-activate the pipeline so it is runnable immediately.
      // Activation generates code and flips status DRAFT → ACTIVE.
      try {
        await activatePipeline.mutateAsync(pipeline.id)
      } catch (activationError) {
        // Non-fatal: pipeline is created but stays in draft.
        console.warn('Pipeline created but activation failed:', activationError)
        toast({
          title: 'Pipeline created (draft)',
          description: `${pipeline.name} was created but could not be activated automatically. You can activate it manually from the pipeline page.`,
          variant: 'destructive',
        })
        navigate(`/app/pipelines/${pipeline.id}`)
        return
      }
      toast({
        title: 'Pipeline created',
        description: `${pipeline.name} has been created and activated successfully.`,
      })
      navigate(`/app/pipelines/${pipeline.id}`)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create pipeline'
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      })
    }
  }

  const handleCancel = () => {
    navigate('/app/pipelines')
  }

  return (
    <div className="container max-w-4xl mx-auto py-8">
      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex justify-between mb-2">
          {STEPS.map((step, index) => (
            <div
              key={step.id}
              className={`flex items-center gap-2 ${
                index <= currentStepIndex ? 'text-primary' : 'text-muted-foreground'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  index < currentStepIndex
                    ? 'bg-primary text-primary-foreground'
                    : index === currentStepIndex
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}
              >
                {index < currentStepIndex ? <Check className="h-4 w-4" /> : index + 1}
              </div>
              <div className="hidden sm:block">
                <p className="font-medium text-sm">{step.title}</p>
                <p className="text-xs text-muted-foreground">{step.description}</p>
              </div>
            </div>
          ))}
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Step content */}
      <Card>
        <CardHeader>
          <CardTitle>Create Data Pipeline</CardTitle>
          <CardDescription>
            Step {currentStepIndex + 1} of {STEPS.length}: {STEPS[currentStepIndex].title}
          </CardDescription>
        </CardHeader>
        <CardContent className="min-h-[400px]">
          {state.currentStep === 'kind' && (
            <SourceKindStep state={state} onStateChange={handleStateChange} />
          )}
          {state.currentStep === 'source' && state.sourceKind === 'sql' && (
            <SourceSelector state={state} onStateChange={handleStateChange} />
          )}
          {state.currentStep === 'source' && state.sourceKind === 'file' && (
            <FileSourceSelector state={state} onStateChange={handleStateChange} />
          )}
          {state.currentStep === 'columns' && (
            <ColumnSelector state={state} onStateChange={handleStateChange} />
          )}
          {state.currentStep === 'target' && (
            <TargetConfiguration state={state} onStateChange={handleStateChange} />
          )}
          {state.currentStep === 'review' && (
            <ReviewStep state={state} />
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleCancel}>
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            {currentStepIndex > 0 && (
              <Button variant="outline" onClick={goPrev}>
                <ChevronLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            )}
          </div>
          <div>
            {currentStepIndex < STEPS.length - 1 ? (
              <Button onClick={goNext} disabled={!canProceed()}>
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleCreate}
                disabled={!canProceed() || createPipeline.isPending || activatePipeline.isPending}
              >
                {createPipeline.isPending || activatePipeline.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Check className="h-4 w-4 mr-2" />
                )}
                Create Pipeline
              </Button>
            )}
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
