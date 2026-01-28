/**
 * Create Model Dialog Component
 */

import { useState } from 'react'
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
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { useCreateSemanticModel } from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { CreateSemanticModelDto, ModelType } from '../types'

const createModelSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .regex(/^[a-z][a-z0-9_]*$/, 'Name must start with letter, only lowercase letters, numbers, and underscores'),
  dbt_model: z.string().min(1, 'dbt model is required'),
  label: z.string().optional(),
  description: z.string().optional(),
  model_type: z.enum(['fact', 'dimension', 'aggregate']).default('fact'),
  cache_enabled: z.boolean().default(true),
  cache_ttl_seconds: z.number().int().min(60).max(86400).default(3600),
  tags: z.string().optional(), // Comma-separated tags
})

type FormData = z.infer<typeof createModelSchema>

interface CreateModelDialogProps {
  children?: React.ReactNode
  open?: boolean
  onClose?: () => void
  onSuccess?: () => void
}

export function CreateModelDialog({ children, open: controlledOpen, onClose, onSuccess }: CreateModelDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const { toast } = useToast()
  const createModel = useCreateSemanticModel()
  
  // Support both controlled and uncontrolled modes
  const isControlled = controlledOpen !== undefined
  const open = isControlled ? controlledOpen : internalOpen
  const setOpen = (value: boolean) => {
    if (isControlled) {
      if (!value && onClose) {
        onClose()
      }
    } else {
      setInternalOpen(value)
    }
  }
  
  const form = useForm<FormData>({
    resolver: zodResolver(createModelSchema),
    defaultValues: {
      name: '',
      dbt_model: '',
      label: '',
      description: '',
      model_type: 'fact',
      cache_enabled: true,
      cache_ttl_seconds: 3600,
      tags: '',
    },
  })
  
  const handleSubmit = async (data: FormData) => {
    try {
      const payload: CreateSemanticModelDto = {
        name: data.name,
        dbt_model: data.dbt_model,
        label: data.label || undefined,
        description: data.description || undefined,
        model_type: data.model_type as ModelType,
        cache_enabled: data.cache_enabled,
        cache_ttl_seconds: data.cache_ttl_seconds,
        tags: data.tags ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
      }
      
      await createModel.mutateAsync(payload)
      
      toast({
        title: 'Model created',
        description: `Semantic model "${data.name}" has been created.`,
      })
      
      setOpen(false)
      form.reset()
      onSuccess?.()
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.error || 'Failed to create model',
      })
    }
  }
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {children && <DialogTrigger asChild>{children}</DialogTrigger>}
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create Semantic Model</DialogTitle>
          <DialogDescription>
            Define a new semantic model based on a dbt model.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              placeholder="sales_orders"
              {...form.register('name')}
              className={form.formState.errors.name ? 'border-destructive' : ''}
            />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">
                {form.formState.errors.name.message}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Unique identifier for the model (snake_case)
            </p>
          </div>
          
          {/* dbt Model */}
          <div className="space-y-2">
            <Label htmlFor="dbt_model">
              dbt Model <span className="text-destructive">*</span>
            </Label>
            <Input
              id="dbt_model"
              placeholder="mart_sales_orders"
              {...form.register('dbt_model')}
              className={form.formState.errors.dbt_model ? 'border-destructive' : ''}
            />
            {form.formState.errors.dbt_model && (
              <p className="text-sm text-destructive">
                {form.formState.errors.dbt_model.message}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Reference to the underlying dbt model
            </p>
          </div>
          
          {/* Label */}
          <div className="space-y-2">
            <Label htmlFor="label">Label</Label>
            <Input
              id="label"
              placeholder="Sales Orders"
              {...form.register('label')}
            />
            <p className="text-xs text-muted-foreground">
              Human-readable display name
            </p>
          </div>
          
          {/* Model Type */}
          <div className="space-y-2">
            <Label>Model Type</Label>
            <Select
              value={form.watch('model_type')}
              onValueChange={(v) => form.setValue('model_type', v as any)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fact">Fact Table</SelectItem>
                <SelectItem value="dimension">Dimension Table</SelectItem>
                <SelectItem value="aggregate">Aggregate Table</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Describe this semantic model..."
              rows={3}
              {...form.register('description')}
            />
          </div>
          
          {/* Cache Settings */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="cache_enabled"
                checked={form.watch('cache_enabled')}
                onCheckedChange={(checked) => form.setValue('cache_enabled', !!checked)}
              />
              <Label htmlFor="cache_enabled" className="font-normal">
                Enable query caching
              </Label>
            </div>
            
            {form.watch('cache_enabled') && (
              <div className="space-y-2 pl-6">
                <Label htmlFor="cache_ttl">Cache TTL (seconds)</Label>
                <Input
                  id="cache_ttl"
                  type="number"
                  min={60}
                  max={86400}
                  {...form.register('cache_ttl_seconds', { valueAsNumber: true })}
                />
              </div>
            )}
          </div>
          
          {/* Tags */}
          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              placeholder="sales, orders, revenue"
              {...form.register('tags')}
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated list of tags
            </p>
          </div>
          
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createModel.isPending}>
              {createModel.isPending ? 'Creating...' : 'Create Model'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
