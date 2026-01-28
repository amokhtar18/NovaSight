/**
 * Measure Editor Component
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
import { useAddMeasure, useUpdateMeasure } from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { Measure, Column, AggregationType, FormatType } from '../types'

const measureSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .regex(/^[a-z][a-z0-9_]*$/, 'Name must start with letter, only lowercase letters, numbers, and underscores'),
  label: z.string().optional(),
  description: z.string().optional(),
  aggregation: z.enum(['sum', 'count', 'count_distinct', 'avg', 'min', 'max', 'median', 'percentile', 'raw']),
  expression: z.string().min(1, 'Expression is required'),
  format: z.enum(['number', 'currency', 'percent']).default('number'),
  format_string: z.string().optional(),
  decimal_places: z.number().int().min(0).max(10).default(2),
  unit: z.string().optional(),
  is_hidden: z.boolean().default(false),
  is_additive: z.boolean().default(true),
  filters: z.string().optional(),
})

type FormData = z.infer<typeof measureSchema>

interface MeasureEditorProps {
  open: boolean
  onClose: () => void
  modelId: string
  measure?: Measure
  availableColumns?: Column[]
}

export function MeasureEditor({
  open,
  onClose,
  modelId,
  measure,
  availableColumns = [],
}: MeasureEditorProps) {
  const { toast } = useToast()
  const addMeasure = useAddMeasure()
  const updateMeasure = useUpdateMeasure()
  
  const isEditing = !!measure
  
  const form = useForm<FormData>({
    resolver: zodResolver(measureSchema),
    defaultValues: {
      name: '',
      label: '',
      description: '',
      aggregation: 'sum',
      expression: '',
      format: 'number',
      format_string: '',
      decimal_places: 2,
      unit: '',
      is_hidden: false,
      is_additive: true,
      filters: '',
    },
  })
  
  // Reset form when measure changes
  useEffect(() => {
    if (measure) {
      form.reset({
        name: measure.name,
        label: measure.label || '',
        description: measure.description || '',
        aggregation: measure.aggregation,
        expression: measure.expression,
        format: measure.format || 'number',
        format_string: measure.format_string || '',
        decimal_places: measure.decimal_places ?? 2,
        unit: measure.unit || '',
        is_hidden: measure.is_hidden,
        is_additive: measure.is_additive,
        filters: measure.filters || '',
      })
    } else {
      form.reset({
        name: '',
        label: '',
        description: '',
        aggregation: 'sum',
        expression: '',
        format: 'number',
        format_string: '',
        decimal_places: 2,
        unit: '',
        is_hidden: false,
        is_additive: true,
        filters: '',
      })
    }
  }, [measure, form])
  
  const handleSubmit = async (data: FormData) => {
    try {
      const payload = {
        ...data,
        aggregation: data.aggregation as AggregationType,
        format: data.format as FormatType,
        label: data.label || undefined,
        description: data.description || undefined,
        format_string: data.format_string || undefined,
        unit: data.unit || undefined,
        filters: data.filters || undefined,
      }
      
      if (isEditing) {
        await updateMeasure.mutateAsync({
          measureId: measure.id,
          modelId,
          data: payload,
        })
        
        toast({
          title: 'Measure updated',
          description: `Measure "${data.name}" has been updated.`,
        })
      } else {
        await addMeasure.mutateAsync({
          modelId,
          data: payload,
        })
        
        toast({
          title: 'Measure added',
          description: `Measure "${data.name}" has been added.`,
        })
      }
      
      onClose()
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || `Failed to ${isEditing ? 'update' : 'add'} measure`,
      })
    }
  }
  
  const isPending = addMeasure.isPending || updateMeasure.isPending
  
  // Auto-suggest format based on aggregation
  const aggregation = form.watch('aggregation')
  useEffect(() => {
    if (aggregation === 'count' || aggregation === 'count_distinct') {
      form.setValue('is_additive', true)
      form.setValue('decimal_places', 0)
    }
  }, [aggregation, form])
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Measure' : 'Add Measure'}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Modify the measure properties.'
              : 'Define a new measure for aggregating data.'}
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
                placeholder="total_revenue"
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
                placeholder="Total Revenue"
                {...form.register('label')}
              />
            </div>
          </div>
          
          {/* Aggregation */}
          <div className="space-y-2">
            <Label>
              Aggregation <span className="text-destructive">*</span>
            </Label>
            <Select
              value={form.watch('aggregation')}
              onValueChange={(v) => form.setValue('aggregation', v as any)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sum">SUM - Sum of values</SelectItem>
                <SelectItem value="count">COUNT - Count of rows</SelectItem>
                <SelectItem value="count_distinct">COUNT DISTINCT - Unique values</SelectItem>
                <SelectItem value="avg">AVG - Average</SelectItem>
                <SelectItem value="min">MIN - Minimum value</SelectItem>
                <SelectItem value="max">MAX - Maximum value</SelectItem>
                <SelectItem value="median">MEDIAN - Median value</SelectItem>
                <SelectItem value="percentile">PERCENTILE - Percentile</SelectItem>
                <SelectItem value="raw">RAW - Custom expression</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Expression */}
          <div className="space-y-2">
            <Label htmlFor="expression">
              Expression <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="expression"
              placeholder="order_total"
              rows={2}
              className={`font-mono text-sm ${form.formState.errors.expression ? 'border-destructive' : ''}`}
              {...form.register('expression')}
            />
            {form.formState.errors.expression && (
              <p className="text-xs text-destructive">
                {form.formState.errors.expression.message}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Column name or SQL expression to aggregate
            </p>
            
            {/* Quick column selection */}
            {availableColumns.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {availableColumns
                  .filter(col => ['Int32', 'Int64', 'Float64', 'Decimal'].some(t => col.data_type.includes(t)))
                  .slice(0, 8)
                  .map((col) => (
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
          
          {/* Format Settings */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Format</Label>
              <Select
                value={form.watch('format')}
                onValueChange={(v) => form.setValue('format', v as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="number">Number</SelectItem>
                  <SelectItem value="currency">Currency</SelectItem>
                  <SelectItem value="percent">Percent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="format_string">Format String</Label>
              <Input
                id="format_string"
                placeholder={form.watch('format') === 'currency' ? '$#,##0.00' : '#,##0.00'}
                {...form.register('format_string')}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="decimal_places">Decimals</Label>
              <Input
                id="decimal_places"
                type="number"
                min={0}
                max={10}
                {...form.register('decimal_places', { valueAsNumber: true })}
              />
            </div>
          </div>
          
          {/* Unit */}
          <div className="space-y-2">
            <Label htmlFor="unit">Unit</Label>
            <Input
              id="unit"
              placeholder="USD, kg, items, etc."
              {...form.register('unit')}
            />
          </div>
          
          {/* Filters */}
          <div className="space-y-2">
            <Label htmlFor="filters">Default Filters (optional)</Label>
            <Textarea
              id="filters"
              placeholder="status = 'completed'"
              rows={2}
              className="font-mono text-sm"
              {...form.register('filters')}
            />
            <p className="text-xs text-muted-foreground">
              SQL WHERE clause to apply to this measure
            </p>
          </div>
          
          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Describe this measure..."
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
                  id="is_hidden"
                  checked={form.watch('is_hidden')}
                  onCheckedChange={(checked) => form.setValue('is_hidden', !!checked)}
                />
                <Label htmlFor="is_hidden" className="font-normal">
                  Hidden from UI
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_additive"
                  checked={form.watch('is_additive')}
                  onCheckedChange={(checked) => form.setValue('is_additive', !!checked)}
                />
                <Label htmlFor="is_additive" className="font-normal">
                  Additive (can be summed)
                </Label>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving...' : isEditing ? 'Save Changes' : 'Add Measure'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
