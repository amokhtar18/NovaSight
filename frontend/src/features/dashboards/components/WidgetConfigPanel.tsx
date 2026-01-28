/**
 * Widget Configuration Panel
 */

import { useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useUpdateWidget } from '../hooks/useDashboards'
import { QueryConfigEditor } from './config/QueryConfigEditor'
import { VizConfigEditor } from './config/VizConfigEditor'
import type { Widget } from '@/types/dashboard'

interface WidgetConfigPanelProps {
  widget: Widget
  onClose: () => void
}

export function WidgetConfigPanel({ widget, onClose }: WidgetConfigPanelProps) {
  const [config, setConfig] = useState({
    name: widget.name,
    type: widget.type,
    query_config: widget.query_config,
    viz_config: widget.viz_config,
  })
  
  const updateMutation = useUpdateWidget(widget.dashboard_id, widget.id)
  
  const handleSave = async () => {
    await updateMutation.mutateAsync(config)
    onClose()
  }
  
  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-card border-l shadow-lg z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="font-semibold">Configure Widget</h2>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      
      <div className="flex-1 overflow-auto p-4">
        <div className="space-y-4">
          <div>
            <Label htmlFor="widget-name">Widget Name</Label>
            <Input
              id="widget-name"
              value={config.name}
              onChange={(e) => setConfig({ ...config, name: e.target.value })}
              placeholder="Enter widget name"
            />
          </div>
          
          <Tabs defaultValue="query" className="w-full">
            <TabsList className="w-full">
              <TabsTrigger value="query" className="flex-1">Query</TabsTrigger>
              <TabsTrigger value="viz" className="flex-1">Visualization</TabsTrigger>
            </TabsList>
            
            <TabsContent value="query" className="mt-4">
              <QueryConfigEditor
                config={config.query_config}
                onChange={(qc) => setConfig({ ...config, query_config: qc })}
              />
            </TabsContent>
            
            <TabsContent value="viz" className="mt-4">
              <VizConfigEditor
                type={config.type}
                config={config.viz_config}
                onChange={(vc) => setConfig({ ...config, viz_config: vc })}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
      
      <div className="p-4 border-t bg-card">
        <div className="flex gap-2">
          <Button variant="outline" onClick={onClose} className="flex-1">
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            className="flex-1"
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>
    </div>
  )
}
