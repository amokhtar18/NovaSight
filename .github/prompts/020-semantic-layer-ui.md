# 020 - Semantic Layer UI

## Metadata

```yaml
prompt_id: "020"
phase: 3
agent: "@frontend"
model: "sonnet 4.5"
priority: P0
estimated_effort: "4 days"
dependencies: ["006", "019"]
```

## Objective

Implement the semantic layer management UI with visual model builder.

## Task Description

Create React components for defining and managing semantic models, dimensions, and measures.

## Requirements

### Semantic Models Page

```tsx
// src/features/semantic/pages/SemanticModelsPage.tsx
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ModelCard } from '../components/ModelCard'
import { CreateModelDialog } from '../components/CreateModelDialog'
import { api } from '@/lib/api'

export function SemanticModelsPage() {
  const { data: models, isLoading } = useQuery({
    queryKey: ['semantic-models'],
    queryFn: () => api.get('/semantic/models').then(r => r.data),
  })
  
  return (
    <div className="container py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Semantic Layer</h1>
          <p className="text-muted-foreground">
            Define dimensions, measures, and relationships
          </p>
        </div>
        <CreateModelDialog>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Model
          </Button>
        </CreateModelDialog>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {models?.map((model) => (
          <ModelCard key={model.id} model={model} />
        ))}
      </div>
    </div>
  )
}
```

### Model Builder Component

```tsx
// src/features/semantic/components/ModelBuilder.tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DimensionList } from './DimensionList'
import { MeasureList } from './MeasureList'
import { RelationshipDiagram } from './RelationshipDiagram'
import { ModelPreview } from './ModelPreview'

interface ModelBuilderProps {
  model: SemanticModel
}

export function ModelBuilder({ model }: ModelBuilderProps) {
  const [activeTab, setActiveTab] = useState('dimensions')
  const queryClient = useQueryClient()
  
  return (
    <div className="grid grid-cols-3 gap-6 h-[calc(100vh-200px)]">
      {/* Left Panel - Configuration */}
      <div className="col-span-2 border rounded-lg overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="border-b px-4">
            <TabsList className="my-2">
              <TabsTrigger value="dimensions">Dimensions</TabsTrigger>
              <TabsTrigger value="measures">Measures</TabsTrigger>
              <TabsTrigger value="relationships">Relationships</TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="dimensions" className="p-4 h-full overflow-auto">
            <DimensionList 
              modelId={model.id} 
              dimensions={model.dimensions}
            />
          </TabsContent>
          
          <TabsContent value="measures" className="p-4 h-full overflow-auto">
            <MeasureList 
              modelId={model.id}
              measures={model.measures}
            />
          </TabsContent>
          
          <TabsContent value="relationships" className="p-4 h-full overflow-auto">
            <RelationshipDiagram 
              modelId={model.id}
              relationships={model.relationships}
            />
          </TabsContent>
        </Tabs>
      </div>
      
      {/* Right Panel - Preview */}
      <div className="border rounded-lg overflow-hidden">
        <div className="border-b p-4">
          <h3 className="font-semibold">Preview</h3>
        </div>
        <div className="p-4">
          <ModelPreview model={model} />
        </div>
      </div>
    </div>
  )
}
```

### Dimension Editor

```tsx
// src/features/semantic/components/DimensionEditor.tsx
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
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { CodeEditor } from '@/components/common/CodeEditor'

const dimensionSchema = z.object({
  name: z.string().min(1).regex(/^[a-z][a-z0-9_]*$/),
  label: z.string().min(1),
  description: z.string().optional(),
  type: z.enum(['categorical', 'temporal', 'numeric']),
  expression: z.string().min(1),
  isPrimaryKey: z.boolean().default(false),
})

interface DimensionEditorProps {
  open: boolean
  onClose: () => void
  onSave: (data: any) => void
  dimension?: Dimension
  availableColumns: Column[]
}

export function DimensionEditor({
  open,
  onClose,
  onSave,
  dimension,
  availableColumns,
}: DimensionEditorProps) {
  const form = useForm({
    resolver: zodResolver(dimensionSchema),
    defaultValues: dimension || {
      type: 'categorical',
      isPrimaryKey: false,
    },
  })
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {dimension ? 'Edit Dimension' : 'Add Dimension'}
          </DialogTitle>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(onSave)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input 
                {...form.register('name')}
                placeholder="order_date"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Label</label>
              <Input 
                {...form.register('label')}
                placeholder="Order Date"
              />
            </div>
          </div>
          
          <div>
            <label className="text-sm font-medium">Type</label>
            <Select 
              value={form.watch('type')}
              onValueChange={(v) => form.setValue('type', v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="categorical">Categorical</SelectItem>
                <SelectItem value="temporal">Temporal</SelectItem>
                <SelectItem value="numeric">Numeric</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <label className="text-sm font-medium">Expression</label>
            <CodeEditor
              language="sql"
              value={form.watch('expression')}
              onChange={(v) => form.setValue('expression', v)}
              placeholder="toDate(created_at)"
              height={100}
            />
            <p className="text-xs text-muted-foreground mt-1">
              SQL expression or column name
            </p>
          </div>
          
          <div>
            <label className="text-sm font-medium">Description</label>
            <Textarea 
              {...form.register('description')}
              placeholder="Describe this dimension..."
            />
          </div>
          
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

### Measure Editor

```tsx
// src/features/semantic/components/MeasureEditor.tsx
// Similar structure to DimensionEditor with aggregation options:
// - SUM, COUNT, COUNT_DISTINCT, AVG, MIN, MAX, MEDIAN
// - Format options: number, currency, percent
// - Default filters
```

## Expected Output

```
frontend/src/features/semantic/
├── components/
│   ├── ModelCard.tsx
│   ├── ModelBuilder.tsx
│   ├── DimensionList.tsx
│   ├── DimensionEditor.tsx
│   ├── MeasureList.tsx
│   ├── MeasureEditor.tsx
│   ├── RelationshipDiagram.tsx
│   └── ModelPreview.tsx
├── pages/
│   ├── SemanticModelsPage.tsx
│   └── ModelDetailPage.tsx
├── hooks/
│   └── useSemanticModels.ts
└── index.ts
```

## Acceptance Criteria

- [ ] List page shows all semantic models
- [ ] Model builder allows adding dimensions
- [ ] Model builder allows adding measures
- [ ] Relationship diagram is interactive
- [ ] Expression editor has syntax highlighting
- [ ] Validation errors displayed clearly
- [ ] Preview shows sample data
- [ ] Changes save correctly

## Reference Documents

- [Semantic Layer API](./019-semantic-layer-api.md)
- [React Components Skill](../skills/react-components/SKILL.md)
