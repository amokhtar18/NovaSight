/**
 * Model Detail Page
 * Page for viewing and editing a specific semantic model
 */

import { useParams, Navigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { ModelBuilder } from '../components/ModelBuilder'
import { useSemanticModel } from '../hooks/useSemanticModels'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'

export function ModelDetailPage() {
  const { modelId } = useParams<{ modelId: string }>()
  
  const { 
    data: model, 
    isLoading, 
    error,
    isError 
  } = useSemanticModel(modelId || '')
  
  // Redirect if no modelId
  if (!modelId) {
    return <Navigate to="/semantic" replace />
  }
  
  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-muted-foreground">Loading semantic model...</p>
          </div>
        </div>
      </div>
    )
  }
  
  // Error state
  if (isError) {
    const errorMessage = (error as any)?.response?.data?.error 
      || (error as Error)?.message 
      || 'Failed to load semantic model'
    
    return (
      <div className="container mx-auto py-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      </div>
    )
  }
  
  // Model not found
  if (!model) {
    return (
      <div className="container mx-auto py-6">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Not Found</AlertTitle>
          <AlertDescription>
            The requested semantic model could not be found.
          </AlertDescription>
        </Alert>
      </div>
    )
  }
  
  return (
    <div className="container mx-auto py-6">
      <ModelBuilder 
        model={model}
        // Available columns would come from the dbt model schema
        availableColumns={[]}
      />
    </div>
  )
}
