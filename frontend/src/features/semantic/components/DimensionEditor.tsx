/**
 * Dimension Editor Component
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAddDimension, useUpdateDimension } from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { Dimension, Column, DimensionType } from '../types'

const dimensionSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .regex(/^[a-z][a-z0-9_]*$/, 'Name must start with letter, only lowercase letters, numbers, and underscores'),
  label: z.string().optional(),
  description: z.string().optional(),
  type: z.enum(['categorical', 'temporal', 'numeric', 'hierarchical']),
  expression: z.string().min(1, 'Expression is required'),
  data_type: z.string().default('String'),
  is_primary_key: z.boolean().default(false),
  is_hidden: z.boolean().default(false),
  is_filterable: z.boolean().default(true),
  is_groupable: z.boolean().default(true),
  format_string: z.string().optional(),
})

type FormData = z.infer<typeof dimensionSchema>

interface DimensionEditorProps {
  open: boolean
  onClose: () => void
  modelId: string
  dimension?: Dimension
  availableColumns?: Column[]
}

export function DimensionEditor({
  open,
  onClose,
  modelId,
  dimension,
  availableColumns = [],
}: DimensionEditorProps) {
  const { toast } = useToast()
  const addDimension = useAddDimension()
  const updateDimension = useUpdateDimension()
  
  const isEditing = !!dimension
  
  const form = useForm<FormData>({
    resolver: zodResolver(dimensionSchema),
    defaultValues: {
      name: '',
      label: '',
      description: '',
      type: 'categorical',
      expression: '',
      data_type: 'String',
      is_primary_key: false,
      is_hidden: false,
      is_filterable: true,
      is_groupable: true,
      format_string: '',
    },
  })
  
  // Reset form when dimension changes
  useEffect(() => {
    if (dimension) {
      form.reset({
        name: dimension.name,
        label: dimension.label || '',
        description: dimension.description || '',
        type: dimension.type,
        expression: dimension.expression,
        data_type: dimension.data_type || 'String',
        is_primary_key: dimension.is_primary_key,
        is_hidden: dimension.is_hidden,
        is_filterable: dimension.is_filterable,
        is_groupable: dimension.is_groupable,
        format_string: dimension.format_string || '',
      })
    } else {
      form.reset({
        name: '',
        label: '',
        description: '',
        type: 'categorical',
        expression: '',
        data_type: 'String',
        is_primary_key: false,
        is_hidden: false,
        is_filterable: true,
        is_groupable: true,
        format_string: '',
      })
    }
  }, [dimension, form])
  
  const handleSubmit = async (data: FormData) => {
    try {
      if (isEditing) {
        await updateDimension.mutateAsync({
          dimensionId: dimension.id,
          modelId,
          data: {
            ...data,
            type: data.type as DimensionType,
            label: data.label || undefined,
            description: data.description || undefined,
            format_string: data.format_string || undefined,
          },
        })
        
        toast({
          title: 'Dimension updated',
          description: `Dimension "${data.name}" has been updated.`,
        })
      } else {
        await addDimension.mutateAsync({
          modelId,
          data: {
            ...data,
            type: data.type as DimensionType,
            label: data.label || undefined,
            description: data.description || undefined,
            format_string: data.format_string || undefined,
          },
        })
        
        toast({
          title: 'Dimension added',
          description: `Dimension "${data.name}" has been added.`,
        })
      }
      
      onClose()
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || `Failed to ${isEditing ? 'update' : 'add'} dimension`,
      })
    }
  }
  
  const isPending = addDimension.isPending || updateDimension.isPending
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Dimension' : 'Add Dimension'}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Modify the dimension properties.'
              : 'Define a new dimension for slicing and grouping data.'}
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                placeholder="order_date"
                {...form.register('name')}
                disabled={isEditing}
                className={form.formState.errors.name ? 'border-destructive' : ''}
              />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>
            
            {/* Label */}
            <div className="space-y-2">
              <Label htmlFor="label">Label</Label>
              <Input
                id="label"
                placeholder="Order Date"
                {...form.register('label')}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            {/* Type */}
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={form.watch('type')}
                onValueChange={(v) => form.setValue('type', v as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="categorical">Categorical</SelectItem>
                  <SelectItem value="temporal">Temporal</SelectItem>
                  <SelectItem value="numeric">Numeric</SelectItem>
                  <SelectItem value="hierarchical">Hierarchical</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {form.watch('type') === 'temporal' && 'Date/time dimension'}
                {form.watch('type') === 'categorical' && 'Text/category dimension'}
                {form.watch('type') === 'numeric' && 'Numeric dimension for binning'}
                {form.watch('type') === 'hierarchical' && 'Part of a drill-down hierarchy'}
              </p>
            </div>
            
            {/* Data Type */}
            <div className="space-y-2">
              <Label>Data Type</Label>
              <Select
                value={form.watch('data_type')}
                onValueChange={(v) => form.setValue('data_type', v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="String">String</SelectItem>
                  <SelectItem value="Int32">Int32</SelectItem>
                  <SelectItem value="Int64">Int64</SelectItem>
                  <SelectItem value="Float64">Float64</SelectItem>
                  <SelectItem value="Date">Date</SelectItem>
                  <SelectItem value="DateTime">DateTime</SelectItem>
                  <SelectItem value="Boolean">Boolean</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          {/* Expression */}
          <div className="space-y-2">
            <Label htmlFor="expression">
              Expression <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Textarea
                id="expression"
                placeholder="column_name or toDate(created_at)"
                rows={3}
                className={`font-mono text-sm ${form.formState.errors.expression ? 'border-destructive' : ''}`}
                {...form.register('expression')}
              />
            </div>
            {form.formState.errors.expression && (
              <p className="text-xs text-destructive">
                {form.formState.errors.expression.message}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              SQL expression or column name
            </p>
            
            {/* Quick column selection */}
            {availableColumns.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {availableColumns.slice(0, 10).map((col) => (
                  <Button
                    key={col.name}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="text-xs h-6"
                    onClick={() => form.setValue('expression', col.name)}
                  >
                    {col.name}
                  </Button>
                ))}
              </div>
            )}
          </div>
          
          {/* Format String (for temporal/numeric) */}
          {(form.watch('type') === 'temporal' || form.watch('type') === 'numeric') && (
            <div className="space-y-2">
              <Label htmlFor="format_string">Format String</Label>
              <Input
                id="format_string"
                placeholder={form.watch('type') === 'temporal' ? 'YYYY-MM-DD' : '#,##0.00'}
                {...form.register('format_string')}
              />
            </div>
          )}
          
          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Describe this dimension..."
              rows={2}
              {...form.register('description')}
            />
          </div>
          
          {/* Flags */}
          <div className="space-y-3">
            <Label>Options</Label>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_primary_key"
                  checked={form.watch('is_primary_key')}
                  onCheckedChange={(checked) => form.setValue('is_primary_key', !!checked)}
                />
                <Label htmlFor="is_primary_key" className="font-normal">
                  Primary Key
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_hidden"
                  checked={form.watch('is_hidden')}
                  onCheckedChange={(checked) => form.setValue('is_hidden', !!checked)}
                />
                <Label htmlFor="is_hidden" className="font-normal">
                  Hidden
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_filterable"
                  checked={form.watch('is_filterable')}
                  onCheckedChange={(checked) => form.setValue('is_filterable', !!checked)}
                />
                <Label htmlFor="is_filterable" className="font-normal">
                  Filterable
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_groupable"
                  checked={form.watch('is_groupable')}
                  onCheckedChange={(checked) => form.setValue('is_groupable', !!checked)}
                />
                <Label htmlFor="is_groupable" className="font-normal">
                  Groupable
                </Label>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving...' : isEditing ? 'Save Changes' : 'Add Dimension'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
