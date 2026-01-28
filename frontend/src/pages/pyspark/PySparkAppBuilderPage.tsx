/**
 * PySpark App Builder Page
 * 
 * Multi-step wizard for creating PySpark applications.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Save, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useToast } from '@/components/ui/use-toast'
import {
  SourceSelector,
  ColumnSelector,
  KeyConfiguration,
  SCDConfiguration,
  TargetConfiguration,
  PySparkPreview,
} from '@/features/pyspark/components'
import { useCreatePySparkApp, useGeneratePySparkCode } from '@/features/pyspark/hooks'
import {
  PySparkWizardState,
  INITIAL_WIZARD_STATE,
  WIZARD_STEPS,
} from '@/types/pyspark'
import { cn } from '@/lib/utils'

export function PySparkAppBuilderPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  
  const [state, setState] = useState<PySparkWizardState>(INITIAL_WIZARD_STATE)
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  
  const createApp = useCreatePySparkApp()
  const generateCode = useGeneratePySparkCode()
  
  const currentStep = WIZARD_STEPS[currentStepIndex]
  const isFirstStep = currentStepIndex === 0
  const isLastStep = currentStepIndex === WIZARD_STEPS.length - 1
  const canProceed = currentStep.isValid(state)
  
  // Update state with partial updates
  const handleStateChange = (updates: Partial<PySparkWizardState>) => {
    setState(prev => ({ ...prev, ...updates }))
  }
  
  // Navigate to previous step
  const handleBack = () => {
    if (!isFirstStep) {
      setCurrentStepIndex(prev => prev - 1)
    }
  }
  
  // Navigate to next step
  const handleNext = () => {
    if (canProceed && !isLastStep) {
      setCurrentStepIndex(prev => prev + 1)
    }
  }
  
  // Save the PySpark app
  const handleSave = async () => {
    try {
      const app = await createApp.mutateAsync({
        name: state.name,
        connection_id: state.connectionId,
        description: state.description || undefined,
        source_type: state.sourceType,
        source_schema: state.sourceSchema || undefined,
        source_table: state.sourceTable || undefined,
        source_query: state.sourceQuery || undefined,
        columns_config: state.selectedColumns.filter(c => c.include),
        primary_key_columns: state.primaryKeyColumns,
        cdc_type: state.cdcType,
        cdc_column: state.cdcColumn || undefined,
        partition_columns: state.partitionColumns,
        scd_type: state.scdType,
        write_mode: state.writeMode,
        target_database: state.targetDatabase || undefined,
        target_table: state.targetTable || undefined,
        target_engine: state.targetEngine,
        options: state.options,
      })
      
      // Generate code after creating
      await generateCode.mutateAsync(app.id)
      
      toast({
        title: 'PySpark App Created',
        description: `Successfully created "${app.name}" and generated code.`,
      })
      
      navigate(`/pyspark/${app.id}`)
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create PySpark app. Please try again.',
        variant: 'destructive',
      })
    }
  }
  
  // Render current step content
  const renderStepContent = () => {
    switch (currentStep.id) {
      case 'source':
        return <SourceSelector state={state} onStateChange={handleStateChange} />
      case 'columns':
        return <ColumnSelector state={state} onStateChange={handleStateChange} />
      case 'keys':
        return <KeyConfiguration state={state} onStateChange={handleStateChange} />
      case 'scd':
        return <SCDConfiguration state={state} onStateChange={handleStateChange} />
      case 'target':
        return <TargetConfiguration state={state} onStateChange={handleStateChange} />
      case 'preview':
        return <PySparkPreview state={state} />
      default:
        return null
    }
  }
  
  return (
    <div className="container max-w-5xl py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Create PySpark App</h1>
        <p className="text-muted-foreground mt-2">
          Configure a PySpark extraction job step by step
        </p>
      </div>
      
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {WIZARD_STEPS.map((step, index) => (
            <div
              key={step.id}
              className={cn(
                "flex items-center",
                index < WIZARD_STEPS.length - 1 && "flex-1"
              )}
            >
              <button
                type="button"
                className={cn(
                  "flex flex-col items-center",
                  index <= currentStepIndex ? "cursor-pointer" : "cursor-not-allowed"
                )}
                onClick={() => index < currentStepIndex && setCurrentStepIndex(index)}
                disabled={index > currentStepIndex}
              >
                <div
                  className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                    index < currentStepIndex && "bg-primary text-primary-foreground",
                    index === currentStepIndex && "bg-primary text-primary-foreground ring-2 ring-primary ring-offset-2",
                    index > currentStepIndex && "bg-muted text-muted-foreground"
                  )}
                >
                  {index + 1}
                </div>
                <span className={cn(
                  "mt-2 text-xs font-medium hidden md:block",
                  index === currentStepIndex && "text-primary",
                  index !== currentStepIndex && "text-muted-foreground"
                )}>
                  {step.title}
                </span>
              </button>
              
              {index < WIZARD_STEPS.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-4",
                    index < currentStepIndex ? "bg-primary" : "bg-muted"
                  )}
                />
              )}
            </div>
          ))}
        </div>
      </div>
      
      {/* Step Content */}
      <Card>
        <CardContent className="pt-6">
          {renderStepContent()}
        </CardContent>
      </Card>
      
      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <Button
          type="button"
          variant="outline"
          onClick={handleBack}
          disabled={isFirstStep}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            Step {currentStepIndex + 1} of {WIZARD_STEPS.length}
          </span>
          
          {isLastStep ? (
            <Button
              type="button"
              onClick={handleSave}
              disabled={!canProceed || createApp.isPending || generateCode.isPending}
            >
              {(createApp.isPending || generateCode.isPending) ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              Save PySpark App
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleNext}
              disabled={!canProceed}
            >
              Next
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

export default PySparkAppBuilderPage
