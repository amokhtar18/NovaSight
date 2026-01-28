/**
 * Relationship Diagram Component
 * Visual representation of model relationships
 */

import { useState } from 'react'
import { Plus, Trash2, ArrowRight, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { 
  useRelationships, 
  useCreateRelationship, 
  useDeleteRelationship,
  useSemanticModels,
} from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { Relationship, RelationshipType, JoinType } from '../types'

interface RelationshipDiagramProps {
  modelId: string
  relationships?: Relationship[]
}

const relationshipTypeLabels: Record<RelationshipType, string> = {
  one_to_one: '1:1',
  one_to_many: '1:N',
  many_to_one: 'N:1',
  many_to_many: 'N:N',
}

const joinTypeColors: Record<JoinType, string> = {
  LEFT: 'bg-blue-100 text-blue-800',
  INNER: 'bg-green-100 text-green-800',
  RIGHT: 'bg-orange-100 text-orange-800',
  FULL: 'bg-purple-100 text-purple-800',
}

export function RelationshipDiagram({ modelId }: RelationshipDiagramProps) {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingRelationship, setDeletingRelationship] = useState<Relationship | undefined>()
  
  // Form state
  const [formData, setFormData] = useState({
    from_model_id: modelId,
    to_model_id: '',
    from_column: '',
    to_column: '',
    relationship_type: 'many_to_one' as RelationshipType,
    join_type: 'LEFT' as JoinType,
  })
  
  const { data: allModels = [] } = useSemanticModels()
  const { data: allRelationships = [] } = useRelationships()
  const createRelationship = useCreateRelationship()
  const deleteRelationship = useDeleteRelationship()
  const { toast } = useToast()
  
  // Filter relationships relevant to this model
  const modelRelationships = allRelationships.filter(
    (r: Relationship) => r.from_model_id === modelId || r.to_model_id === modelId
  )
  
  // Other models for relationship creation
  const otherModels = allModels.filter((m: { id: string }) => m.id !== modelId)
  
  const handleCreateSubmit = async () => {
    try {
      await createRelationship.mutateAsync({
        from_model_id: formData.from_model_id,
        to_model_id: formData.to_model_id,
        from_column: formData.from_column,
        to_column: formData.to_column,
        relationship_type: formData.relationship_type,
        join_type: formData.join_type,
      })
      
      toast({
        title: 'Relationship created',
        description: 'The relationship has been created.',
      })
      
      setCreateDialogOpen(false)
      setFormData({
        from_model_id: modelId,
        to_model_id: '',
        from_column: '',
        to_column: '',
        relationship_type: 'many_to_one',
        join_type: 'LEFT',
      })
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || 'Failed to create relationship',
      })
    }
  }
  
  const handleDeleteClick = (relationship: Relationship) => {
    setDeletingRelationship(relationship)
    setDeleteDialogOpen(true)
  }
  
  const handleDeleteConfirm = async () => {
    if (!deletingRelationship) return
    
    try {
      await deleteRelationship.mutateAsync(deletingRelationship.id)
      
      toast({
        title: 'Relationship deleted',
        description: 'The relationship has been deleted.',
      })
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || 'Failed to delete relationship',
      })
    } finally {
      setDeleteDialogOpen(false)
      setDeletingRelationship(undefined)
    }
  }
  
  const getModelName = (id: string) => {
    const model = allModels.find((m: { id: string; label?: string; name: string }) => m.id === id)
    return model?.label || model?.name || id
  }
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Relationships</h3>
          <p className="text-sm text-muted-foreground">
            Define how this model joins with other models
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)} disabled={otherModels.length === 0}>
          <Plus className="h-4 w-4 mr-2" />
          Add Relationship
        </Button>
      </div>
      
      {modelRelationships.length === 0 ? (
        <div className="text-center py-12 border rounded-lg bg-muted/30">
          <Link2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h4 className="text-lg font-medium mb-2">No relationships yet</h4>
          <p className="text-muted-foreground mb-4">
            Add relationships to join this model with other models.
          </p>
          {otherModels.length > 0 ? (
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add First Relationship
            </Button>
          ) : (
            <p className="text-sm text-muted-foreground">
              Create more models to define relationships.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {modelRelationships.map((relationship: Relationship) => {
            const isFromModel = relationship.from_model_id === modelId
            // Use otherModelId for display purposes
            const _otherModelId = isFromModel ? relationship.to_model_id : relationship.from_model_id
            void _otherModelId // Suppress unused variable warning
            
            return (
              <Card key={relationship.id}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* From Model */}
                      <div className="text-center">
                        <div className="font-medium">
                          {getModelName(relationship.from_model_id)}
                        </div>
                        <code className="text-xs bg-muted px-2 py-0.5 rounded">
                          {relationship.from_column}
                        </code>
                      </div>
                      
                      {/* Arrow with relationship info */}
                      <div className="flex flex-col items-center gap-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">
                            {relationshipTypeLabels[relationship.relationship_type]}
                          </Badge>
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                          <Badge className={joinTypeColors[relationship.join_type]}>
                            {relationship.join_type}
                          </Badge>
                        </div>
                      </div>
                      
                      {/* To Model */}
                      <div className="text-center">
                        <div className="font-medium">
                          {getModelName(relationship.to_model_id)}
                        </div>
                        <code className="text-xs bg-muted px-2 py-0.5 rounded">
                          {relationship.to_column}
                        </code>
                      </div>
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDeleteClick(relationship)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
      
      {/* Create Relationship Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Relationship</DialogTitle>
            <DialogDescription>
              Define how this model relates to another model.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* To Model */}
            <div className="space-y-2">
              <Label>Related Model</Label>
              <Select
                value={formData.to_model_id}
                onValueChange={(v) => setFormData(prev => ({ ...prev, to_model_id: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  {otherModels.map((model: { id: string; label?: string; name: string }) => (
                    <SelectItem key={model.id} value={model.id}>
                      {model.label || model.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Columns */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>From Column (this model)</Label>
                <Input
                  placeholder="customer_id"
                  value={formData.from_column}
                  onChange={(e) => setFormData(prev => ({ ...prev, from_column: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label>To Column (related model)</Label>
                <Input
                  placeholder="id"
                  value={formData.to_column}
                  onChange={(e) => setFormData(prev => ({ ...prev, to_column: e.target.value }))}
                />
              </div>
            </div>
            
            {/* Relationship Type */}
            <div className="space-y-2">
              <Label>Relationship Type</Label>
              <Select
                value={formData.relationship_type}
                onValueChange={(v) => setFormData(prev => ({ ...prev, relationship_type: v as RelationshipType }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="one_to_one">One to One (1:1)</SelectItem>
                  <SelectItem value="one_to_many">One to Many (1:N)</SelectItem>
                  <SelectItem value="many_to_one">Many to One (N:1)</SelectItem>
                  <SelectItem value="many_to_many">Many to Many (N:N)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Join Type */}
            <div className="space-y-2">
              <Label>Join Type</Label>
              <Select
                value={formData.join_type}
                onValueChange={(v) => setFormData(prev => ({ ...prev, join_type: v as JoinType }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LEFT">LEFT JOIN - All from this model</SelectItem>
                  <SelectItem value="INNER">INNER JOIN - Only matching rows</SelectItem>
                  <SelectItem value="RIGHT">RIGHT JOIN - All from related model</SelectItem>
                  <SelectItem value="FULL">FULL JOIN - All from both models</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleCreateSubmit}
              disabled={!formData.to_model_id || !formData.from_column || !formData.to_column || createRelationship.isPending}
            >
              {createRelationship.isPending ? 'Creating...' : 'Create Relationship'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Relationship</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this relationship?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
