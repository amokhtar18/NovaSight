/**
 * Measure List Component
 */

import { useState } from 'react'
import { Plus, Edit, Trash2, EyeOff, Calculator } from 'lucide-react'
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
import { MeasureEditor } from './MeasureEditor'
import { useDeleteMeasure } from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { Measure, Column } from '../types'

interface MeasureListProps {
  modelId: string
  measures: Measure[]
  availableColumns?: Column[]
}

const aggregationColors: Record<string, string> = {
  sum: 'bg-green-100 text-green-800',
  count: 'bg-blue-100 text-blue-800',
  count_distinct: 'bg-indigo-100 text-indigo-800',
  avg: 'bg-orange-100 text-orange-800',
  min: 'bg-cyan-100 text-cyan-800',
  max: 'bg-red-100 text-red-800',
  median: 'bg-purple-100 text-purple-800',
  percentile: 'bg-pink-100 text-pink-800',
  raw: 'bg-gray-100 text-gray-800',
}

const formatIcons: Record<string, string> = {
  number: '#',
  currency: '$',
  percent: '%',
}

export function MeasureList({ modelId, measures, availableColumns = [] }: MeasureListProps) {
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingMeasure, setEditingMeasure] = useState<Measure | undefined>()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingMeasure, setDeletingMeasure] = useState<Measure | undefined>()
  
  const deleteMeasure = useDeleteMeasure()
  const { toast } = useToast()
  
  const handleAdd = () => {
    setEditingMeasure(undefined)
    setEditorOpen(true)
  }
  
  const handleEdit = (measure: Measure) => {
    setEditingMeasure(measure)
    setEditorOpen(true)
  }
  
  const handleDeleteClick = (measure: Measure) => {
    setDeletingMeasure(measure)
    setDeleteDialogOpen(true)
  }
  
  const handleDeleteConfirm = async () => {
    if (!deletingMeasure) return
    
    try {
      await deleteMeasure.mutateAsync({
        measureId: deletingMeasure.id,
        modelId,
      })
      
      toast({
        title: 'Measure deleted',
        description: `Measure "${deletingMeasure.name}" has been deleted.`,
      })
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || 'Failed to delete measure',
      })
    } finally {
      setDeleteDialogOpen(false)
      setDeletingMeasure(undefined)
    }
  }
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Measures</h3>
          <p className="text-sm text-muted-foreground">
            Aggregated metrics and calculations
          </p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          Add Measure
        </Button>
      </div>
      
      {measures.length === 0 ? (
        <div className="text-center py-12 border rounded-lg bg-muted/30">
          <Calculator className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h4 className="text-lg font-medium mb-2">No measures yet</h4>
          <p className="text-muted-foreground mb-4">
            Add measures to define metrics and aggregations.
          </p>
          <Button onClick={handleAdd}>
            <Plus className="h-4 w-4 mr-2" />
            Add First Measure
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Aggregation</TableHead>
                <TableHead>Expression</TableHead>
                <TableHead>Format</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {measures.map((measure) => (
                <TableRow key={measure.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        {measure.label || measure.name}
                        {measure.is_hidden && (
                          <EyeOff className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {measure.name}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="secondary"
                      className={aggregationColors[measure.aggregation] || 'bg-gray-100'}
                    >
                      {measure.aggregation.toUpperCase().replace('_', ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted px-2 py-1 rounded">
                      {measure.expression}
                    </code>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">
                        {formatIcons[measure.format] || '#'}
                      </span>
                      {measure.format_string && (
                        <span className="text-xs text-muted-foreground">
                          {measure.format_string}
                        </span>
                      )}
                      {measure.unit && (
                        <span className="text-xs text-muted-foreground">
                          ({measure.unit})
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(measure)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteClick(measure)}
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
      
      {/* Measure Editor Dialog */}
      <MeasureEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        modelId={modelId}
        measure={editingMeasure}
        availableColumns={availableColumns}
      />
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Measure</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the measure "{deletingMeasure?.name}"?
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
