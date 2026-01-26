# 015 - Data Source UI

## Metadata

```yaml
prompt_id: "015"
phase: 2
agent: "@frontend"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["006", "014"]
```

## Objective

Implement the data source management UI with connection wizard and schema browser.

## Task Description

Create React components for managing data source connections with intuitive UX.

## Requirements

### Data Sources List Page

```tsx
// src/features/datasources/pages/DataSourcesPage.tsx
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { DataSourceCard } from '../components/DataSourceCard'
import { CreateDataSourceDialog } from '../components/CreateDataSourceDialog'
import { api } from '@/lib/api'

export function DataSourcesPage() {
  const { data: datasources, isLoading } = useQuery({
    queryKey: ['datasources'],
    queryFn: () => api.get('/datasources').then(r => r.data),
  })
  
  return (
    <div className="container py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Data Sources</h1>
          <p className="text-muted-foreground">
            Connect and manage your data sources
          </p>
        </div>
        <CreateDataSourceDialog />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {datasources?.map((ds) => (
          <DataSourceCard key={ds.id} datasource={ds} />
        ))}
      </div>
    </div>
  )
}
```

### Connection Wizard

```tsx
// src/features/datasources/components/ConnectionWizard.tsx
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader,
  DialogTitle 
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Stepper } from '@/components/ui/stepper'

const steps = [
  { id: 'type', title: 'Select Type' },
  { id: 'connection', title: 'Connection Details' },
  { id: 'test', title: 'Test Connection' },
  { id: 'tables', title: 'Select Tables' },
]

const connectionSchema = z.object({
  name: z.string().min(1, 'Name required'),
  type: z.enum(['postgresql', 'mysql', 'mongodb']),
  host: z.string().min(1),
  port: z.number().min(1).max(65535),
  database: z.string().min(1),
  username: z.string().min(1),
  password: z.string().min(1),
  ssl: z.boolean().default(true),
})

export function ConnectionWizard({ open, onClose }) {
  const [step, setStep] = useState(0)
  const [connectionResult, setConnectionResult] = useState(null)
  
  const form = useForm({
    resolver: zodResolver(connectionSchema),
    defaultValues: {
      ssl: true,
      port: 5432,
    },
  })
  
  const testMutation = useMutation({
    mutationFn: (data) => api.post('/datasources/test', data),
    onSuccess: (result) => {
      setConnectionResult(result)
      if (result.success) setStep(3)
    },
  })
  
  const createMutation = useMutation({
    mutationFn: (data) => api.post('/datasources', data),
    onSuccess: () => {
      onClose()
      // Invalidate queries
    },
  })
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Connect Data Source</DialogTitle>
        </DialogHeader>
        
        <Stepper steps={steps} currentStep={step} />
        
        {step === 0 && <DataSourceTypeSelector onSelect={...} />}
        {step === 1 && <ConnectionForm form={form} />}
        {step === 2 && <ConnectionTest result={connectionResult} />}
        {step === 3 && <TableSelector datasource={...} />}
      </DialogContent>
    </Dialog>
  )
}
```

### Schema Browser Component

```tsx
// src/features/datasources/components/SchemaBrowser.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Table, Database } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

interface SchemaBrowserProps {
  datasourceId: string
  onTableSelect?: (schema: string, table: string) => void
}

export function SchemaBrowser({ datasourceId, onTableSelect }: SchemaBrowserProps) {
  const { data: schema } = useQuery({
    queryKey: ['datasource-schema', datasourceId],
    queryFn: () => api.get(`/datasources/${datasourceId}/schema`).then(r => r.data),
  })
  
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-4">
        <Database className="h-5 w-5" />
        <span className="font-medium">Database Schema</span>
      </div>
      
      <div className="space-y-2">
        {schema?.schemas.map((s) => (
          <SchemaItem 
            key={s.name} 
            schema={s} 
            onTableSelect={onTableSelect}
          />
        ))}
      </div>
    </div>
  )
}

function SchemaItem({ schema, onTableSelect }) {
  const [isOpen, setIsOpen] = useState(false)
  
  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex items-center gap-2 w-full p-2 hover:bg-muted rounded">
        <ChevronRight className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
        <span>{schema.name}</span>
        <span className="text-muted-foreground ml-auto">{schema.tables.length} tables</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="pl-6 space-y-1">
        {schema.tables.map((table) => (
          <button
            key={table.name}
            onClick={() => onTableSelect?.(schema.name, table.name)}
            className="flex items-center gap-2 w-full p-2 hover:bg-muted rounded text-sm"
          >
            <Table className="h-4 w-4" />
            <span>{table.name}</span>
            <span className="text-muted-foreground ml-auto">{table.row_count} rows</span>
          </button>
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}
```

## Expected Output

```
frontend/src/features/datasources/
├── components/
│   ├── DataSourceCard.tsx
│   ├── ConnectionWizard.tsx
│   ├── DataSourceTypeSelector.tsx
│   ├── ConnectionForm.tsx
│   ├── SchemaBrowser.tsx
│   ├── TableSelector.tsx
│   └── SyncStatus.tsx
├── pages/
│   ├── DataSourcesPage.tsx
│   └── DataSourceDetailPage.tsx
├── hooks/
│   ├── useDataSources.ts
│   └── useDataSourceSchema.ts
└── index.ts
```

## Acceptance Criteria

- [ ] List page shows all data sources
- [ ] Connection wizard guides user through setup
- [ ] Connection test shows success/failure
- [ ] Schema browser displays tables and columns
- [ ] Sync status updates in real-time
- [ ] Error states handled gracefully
- [ ] Loading states with skeletons
- [ ] Responsive design works on mobile

## Reference Documents

- [React Components Skill](../skills/react-components/SKILL.md)
- [Data Source API](./014-data-source-api.md)
