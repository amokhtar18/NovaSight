/**
 * Model Settings Component
 * Dialog for editing semantic model settings
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUpdateSemanticModel } from '../hooks/useSemanticModels'
import { useToast } from '@/components/ui/use-toast'
import type { SemanticModel, ModelType } from '../types'

const modelSettingsSchema = z.object({
  label: z.string().min(1, 'Label is required'),
  description: z.string().optional(),
  model_type: z.enum(['dimension', 'fact', 'aggregate', 'view'] as const),
  is_active: z.boolean(),
  cache_enabled: z.boolean(),
  cache_ttl_seconds: z.coerce.number().min(0).optional(),
  tags: z.string().optional(),
})

type ModelSettingsFormData = z.infer<typeof modelSettingsSchema>

interface ModelSettingsProps {
  open: boolean
  onClose: () => void
  model: SemanticModel
}

export function ModelSettings({ open, onClose, model }: ModelSettingsProps) {
  const updateModel = useUpdateSemanticModel()
  const { toast } = useToast()
  
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ModelSettingsFormData>({
    resolver: zodResolver(modelSettingsSchema),
    defaultValues: {
      label: model.label || model.name,
      description: model.description || '',
      model_type: model.model_type,
      is_active: model.is_active,
      cache_enabled: model.cache_enabled,
      cache_ttl_seconds: model.cache_ttl_seconds || 3600,
      tags: model.tags?.join(', ') || '',
    },
  })
  
  const modelType = watch('model_type')
  const isActive = watch('is_active')
  const cacheEnabled = watch('cache_enabled')
  
  const onSubmit = async (data: ModelSettingsFormData) => {
    try {
      await updateModel.mutateAsync({
        id: model.id,
        data: {
          label: data.label,
          description: data.description,
          model_type: data.model_type as ModelType,
          is_active: data.is_active,
          cache_enabled: data.cache_enabled,
          cache_ttl_seconds: data.cache_ttl_seconds,
          tags: data.tags 
            ? data.tags.split(',').map(t => t.trim()).filter(Boolean)
            : [],
        },
      })
      
      toast({
        title: 'Settings saved',
        description: 'Model settings have been updated.',
      })
      
      onClose()
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: string } } }
      toast({
        variant: 'destructive',
        title: 'Error',
        description: err.response?.data?.error || 'Failed to update settings',
      })
    }
  }
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Model Settings</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Label */}
          <div className="space-y-2">
            <Label htmlFor="label">Display Label</Label>
            <Input
              id="label"
              {...register('label')}
              placeholder="e.g., Sales Transactions"
            />
            {errors.label && (
              <p className="text-sm text-destructive">{errors.label.message}</p>
            )}
          </div>
          
          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Describe what this model represents..."
              rows={3}
            />
          </div>
          
          {/* Model Type */}
          <div className="space-y-2">
            <Label>Model Type</Label>
            <Select 
              value={modelType}
              onValueChange={(v) => setValue('model_type', v as ModelType)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dimension">Dimension</SelectItem>
                <SelectItem value="fact">Fact</SelectItem>
                <SelectItem value="aggregate">Aggregate</SelectItem>
                <SelectItem value="view">View</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Tags */}
          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              {...register('tags')}
              placeholder="sales, revenue, orders"
            />
            <p className="text-sm text-muted-foreground">
              Comma-separated list of tags
            </p>
          </div>
          
          <div className="border-t pt-4 space-y-4">
            {/* Active toggle */}
            <div className="flex items-center justify-between">
              <div>
                <Label>Active</Label>
                <p className="text-sm text-muted-foreground">
                  Make this model available for queries
                </p>
              </div>
              <Checkbox
                checked={isActive}
                onCheckedChange={(checked) => setValue('is_active', checked === true)}
              />
            </div>
            
            {/* Cache toggle */}
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Caching</Label>
                <p className="text-sm text-muted-foreground">
                  Cache query results for better performance
                </p>
              </div>
              <Checkbox
                checked={cacheEnabled}
                onCheckedChange={(checked) => setValue('cache_enabled', checked === true)}
              />
            </div>
            
            {/* Cache TTL */}
            {cacheEnabled && (
              <div className="space-y-2">
                <Label htmlFor="cache_ttl_seconds">Cache TTL (seconds)</Label>
                <Input
                  id="cache_ttl_seconds"
                  type="number"
                  {...register('cache_ttl_seconds')}
                  placeholder="3600"
                  min={0}
                />
                <p className="text-sm text-muted-foreground">
                  How long to cache results (default: 3600 = 1 hour)
                </p>
              </div>
            )}
          </div>
          
          <DialogFooter className="pt-4">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateModel.isPending}>
              {updateModel.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
