/**
 * Add Widget Dialog Component
 */

import { useState } from 'react'
import { Plus } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateWidget } from '../hooks/useDashboards'
import type { WidgetType } from '@/types/dashboard'

interface AddWidgetDialogProps {
  dashboardId: string
}

const WIDGET_TYPES: { value: WidgetType; label: string }[] = [
  { value: 'metric_card', label: 'Metric Card' },
  { value: 'bar_chart', label: 'Bar Chart' },
  { value: 'line_chart', label: 'Line Chart' },
  { value: 'pie_chart', label: 'Pie Chart' },
  { value: 'area_chart', label: 'Area Chart' },
  { value: 'table', label: 'Data Table' },
  { value: 'scatter_chart', label: 'Scatter Chart' },
]

export function AddWidgetDialog({ dashboardId }: AddWidgetDialogProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [type, setType] = useState<WidgetType>('metric_card')
  const createMutation = useCreateWidget(dashboardId)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Find next available position
    const newWidget = {
      name,
      type,
      query_config: {
        dimensions: [],
        measures: [],
        filters: [],
      },
      viz_config: {},
      grid_position: {
        x: 0,
        y: 0,
        w: 4,
        h: 3,
      },
    }
    
    await createMutation.mutateAsync(newWidget)
    setOpen(false)
    setName('')
    setType('metric_card')
  }
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button 
          className="fixed bottom-6 right-6 rounded-full shadow-lg"
          size="lg"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Widget
        </Button>
      </DialogTrigger>
      
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Widget</DialogTitle>
          <DialogDescription>
            Create a new widget for your dashboard
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Widget Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Monthly Revenue"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="type">Widget Type</Label>
            <Select value={type} onValueChange={(v) => setType(v as WidgetType)}>
              <SelectTrigger id="type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WIDGET_TYPES.map((wt) => (
                  <SelectItem key={wt.value} value={wt.value}>
                    {wt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              Create Widget
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
