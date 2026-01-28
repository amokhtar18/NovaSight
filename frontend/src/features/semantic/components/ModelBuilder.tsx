/**
 * Model Builder Component
 * Main component for building and editing semantic models
 */

import { useState } from 'react'
import { ArrowLeft, Settings, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { DimensionList } from './DimensionList'
import { MeasureList } from './MeasureList'
import { RelationshipDiagram } from './RelationshipDiagram'
import { ModelPreview } from './ModelPreview'
import { ModelSettings } from './ModelSettings'
import { useDeleteSemanticModel } from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { SemanticModel, Column } from '../types'

interface ModelBuilderProps {
  model: SemanticModel
  availableColumns?: Column[]
}

export function ModelBuilder({ model, availableColumns = [] }: ModelBuilderProps) {
  const [activeTab, setActiveTab] = useState('dimensions')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  
  const navigate = useNavigate()
  const deleteModel = useDeleteSemanticModel()
  const { toast } = useToast()
  
  const handleDelete = async () => {
    try {
      await deleteModel.mutateAsync(model.id)
      
      toast({
        title: 'Model deleted',
        description: `Semantic model "${model.name}" has been deleted.`,
      })
      
      navigate('/semantic')
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || 'Failed to delete model',
      })
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Link to="/semantic">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">
                {model.label || model.name}
              </h1>
              <Badge variant={model.is_active ? 'default' : 'secondary'}>
                {model.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-1">
              {model.description || `Based on ${model.dbt_model}`}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setSettingsOpen(true)}>
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setDeleteDialogOpen(true)}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Configuration */}
        <div className="lg:col-span-2">
          <div className="border rounded-lg overflow-hidden bg-card">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <div className="border-b px-4">
                <TabsList className="my-2">
                  <TabsTrigger value="dimensions" className="relative">
                    Dimensions
                    {(model.dimensions?.length || 0) > 0 && (
                      <Badge variant="secondary" className="ml-2 h-5 text-xs">
                        {model.dimensions?.length}
                      </Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="measures" className="relative">
                    Measures
                    {(model.measures?.length || 0) > 0 && (
                      <Badge variant="secondary" className="ml-2 h-5 text-xs">
                        {model.measures?.length}
                      </Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="relationships">
                    Relationships
                  </TabsTrigger>
                </TabsList>
              </div>
              
              <TabsContent value="dimensions" className="p-4 m-0">
                <DimensionList 
                  modelId={model.id} 
                  dimensions={model.dimensions || []}
                  availableColumns={availableColumns}
                />
              </TabsContent>
              
              <TabsContent value="measures" className="p-4 m-0">
                <MeasureList 
                  modelId={model.id}
                  measures={model.measures || []}
                  availableColumns={availableColumns}
                />
              </TabsContent>
              
              <TabsContent value="relationships" className="p-4 m-0">
                <RelationshipDiagram 
                  modelId={model.id}
                />
              </TabsContent>
            </Tabs>
          </div>
        </div>
        
        {/* Right Panel - Preview */}
        <div className="lg:col-span-1">
          <div className="border rounded-lg overflow-hidden bg-card sticky top-4">
            <div className="border-b p-4">
              <h3 className="font-semibold">Preview</h3>
            </div>
            <div className="p-4">
              <ModelPreview model={model} />
            </div>
          </div>
        </div>
      </div>
      
      {/* Settings Dialog */}
      <ModelSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        model={model}
      />
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Semantic Model</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{model.label || model.name}"?
              This will also delete all dimensions, measures, and relationships.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete Model
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
