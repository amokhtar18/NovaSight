/**
 * Dimension List Component
 */

import { useState } from 'react'
import { Plus, Edit, Trash2, Eye, EyeOff, Key, Filter, LayoutGrid } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
import { DimensionEditor } from './DimensionEditor'
import { useDeleteDimension } from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { Dimension, Column } from '../types'

interface DimensionListProps {
  modelId: string
  dimensions: Dimension[]
  availableColumns?: Column[]
}

const typeColors = {
  categorical: 'bg-blue-100 text-blue-800',
  temporal: 'bg-orange-100 text-orange-800',
  numeric: 'bg-green-100 text-green-800',
  hierarchical: 'bg-purple-100 text-purple-800',
}

export function DimensionList({ modelId, dimensions, availableColumns = [] }: DimensionListProps) {
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingDimension, setEditingDimension] = useState<Dimension | undefined>()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingDimension, setDeletingDimension] = useState<Dimension | undefined>()
  
  const deleteDimension = useDeleteDimension()
  const { toast } = useToast()
  
  const handleAdd = () => {
    setEditingDimension(undefined)
    setEditorOpen(true)
  }
  
  const handleEdit = (dimension: Dimension) => {
    setEditingDimension(dimension)
    setEditorOpen(true)
  }
  
  const handleDeleteClick = (dimension: Dimension) => {
    setDeletingDimension(dimension)
    setDeleteDialogOpen(true)
  }
  
  const handleDeleteConfirm = async () => {
    if (!deletingDimension) return
    
    try {
      await deleteDimension.mutateAsync({
        dimensionId: deletingDimension.id,
        modelId,
      })
      
      toast({
        title: 'Dimension deleted',
        description: `Dimension "${deletingDimension.name}" has been deleted.`,
      })
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || 'Failed to delete dimension',
      })
    } finally {
      setDeleteDialogOpen(false)
      setDeletingDimension(undefined)
    }
  }
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Dimensions</h3>
          <p className="text-sm text-muted-foreground">
            Attributes for slicing and dicing data
          </p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          Add Dimension
        </Button>
      </div>
      
      {dimensions.length === 0 ? (
        <div className="text-center py-12 border rounded-lg bg-muted/30">
          <LayoutGrid className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h4 className="text-lg font-medium mb-2">No dimensions yet</h4>
          <p className="text-muted-foreground mb-4">
            Add dimensions to define how data can be sliced and grouped.
          </p>
          <Button onClick={handleAdd}>
            <Plus className="h-4 w-4 mr-2" />
            Add First Dimension
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Expression</TableHead>
                <TableHead>Flags</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {dimensions.map((dimension) => (
                <TableRow key={dimension.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        {dimension.label || dimension.name}
                        {dimension.is_primary_key && (
                          <Key className="h-3.5 w-3.5 text-amber-500" />
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {dimension.name}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="secondary"
                      className={typeColors[dimension.type]}
                    >
                      {dimension.type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted px-2 py-1 rounded">
                      {dimension.expression}
                    </code>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {dimension.is_hidden ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-green-500" />
                      )}
                      {dimension.is_filterable && (
                        <Filter className="h-4 w-4 text-blue-500" />
                      )}
                      {dimension.is_groupable && (
                        <LayoutGrid className="h-4 w-4 text-purple-500" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(dimension)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteClick(dimension)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      
      {/* Dimension Editor Dialog */}
      <DimensionEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        modelId={modelId}
        dimension={editingDimension}
        availableColumns={availableColumns}
      />
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Dimension</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the dimension "{deletingDimension?.name}"?
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
