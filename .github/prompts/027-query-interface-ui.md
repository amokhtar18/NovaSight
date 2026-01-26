# 027 - Query Interface UI

## Metadata

```yaml
prompt_id: "027"
phase: 4
agent: "@frontend"
model: "sonnet 4.5"
priority: P0
estimated_effort: "4 days"
dependencies: ["023", "026"]
```

## Objective

Implement the natural language query interface for ad-hoc analytics.

## Task Description

Create a query interface that allows users to ask questions in natural language and see results.

## Requirements

### Query Interface Page

```tsx
// src/features/query/pages/QueryPage.tsx
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { SendIcon, WandIcon, HistoryIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { QueryResult } from '../components/QueryResult'
import { QueryHistory } from '../components/QueryHistory'
import { QuerySuggestions } from '../components/QuerySuggestions'
import { api } from '@/lib/api'

export function QueryPage() {
  const [query, setQuery] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  
  const queryMutation = useMutation({
    mutationFn: (q: string) => api.post('/assistant/query', { query: q }),
  })
  
  const handleSubmit = () => {
    if (query.trim()) {
      queryMutation.mutate(query)
    }
  }
  
  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    queryMutation.mutate(suggestion)
  }
  
  return (
    <div className="container py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Ask Your Data</h1>
          <p className="text-muted-foreground">
            Ask questions in natural language to explore your data
          </p>
        </div>
        <Button 
          variant="outline" 
          onClick={() => setShowHistory(!showHistory)}
        >
          <HistoryIcon className="h-4 w-4 mr-2" />
          History
        </Button>
      </div>
      
      {/* Query Input */}
      <div className="relative mb-6">
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., What were the total sales by region last month?"
          className="min-h-[100px] pr-24 text-lg"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && e.metaKey) {
              handleSubmit()
            }
          }}
        />
        <div className="absolute right-2 bottom-2 flex gap-2">
          <Button 
            size="sm" 
            variant="ghost"
            onClick={() => {/* AI suggestions */}}
          >
            <WandIcon className="h-4 w-4" />
          </Button>
          <Button 
            size="sm"
            onClick={handleSubmit}
            disabled={!query.trim() || queryMutation.isPending}
          >
            <SendIcon className="h-4 w-4 mr-1" />
            {queryMutation.isPending ? 'Thinking...' : 'Ask'}
          </Button>
        </div>
      </div>
      
      {/* Suggestions */}
      {!queryMutation.data && (
        <QuerySuggestions onSelect={handleSuggestionClick} />
      )}
      
      {/* Loading State */}
      {queryMutation.isPending && (
        <QueryLoadingState />
      )}
      
      {/* Results */}
      {queryMutation.data && (
        <QueryResult result={queryMutation.data.data} />
      )}
      
      {/* Error */}
      {queryMutation.error && (
        <QueryError error={queryMutation.error} />
      )}
      
      {/* History Sidebar */}
      {showHistory && (
        <QueryHistory 
          onSelect={(q) => setQuery(q)}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  )
}
```

### Query Result Component

```tsx
// src/features/query/components/QueryResult.tsx
import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChartWrapper } from '@/features/dashboards/components/widgets/ChartWrapper'
import { DataTable } from '@/features/dashboards/components/widgets/DataTable'
import { CodeBlock } from '@/components/common/CodeBlock'
import { SaveToDashboardDialog } from './SaveToDashboardDialog'

interface QueryResultProps {
  result: {
    intent: {
      query_type: string
      dimensions: string[]
      measures: string[]
    }
    data: {
      columns: string[]
      rows: any[]
    }
    sql: string
    explanation: string
  }
}

export function QueryResult({ result }: QueryResultProps) {
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart')
  
  const suggestedChartType = getSuggestedChartType(result.intent)
  
  return (
    <div className="space-y-4">
      {/* Explanation */}
      <Card>
        <CardContent className="pt-4">
          <p className="text-muted-foreground">{result.explanation}</p>
        </CardContent>
      </Card>
      
      {/* Results */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Results</CardTitle>
          <div className="flex items-center gap-2">
            <Tabs value={viewMode} onValueChange={setViewMode}>
              <TabsList>
                <TabsTrigger value="chart">Chart</TabsTrigger>
                <TabsTrigger value="table">Table</TabsTrigger>
              </TabsList>
            </Tabs>
            <SaveToDashboardDialog 
              queryConfig={{
                dimensions: result.intent.dimensions,
                measures: result.intent.measures,
              }}
              chartType={suggestedChartType}
            />
          </div>
        </CardHeader>
        <CardContent>
          {viewMode === 'chart' ? (
            <div className="h-[400px]">
              <ChartWrapper
                type={suggestedChartType}
                data={transformDataForChart(result.data)}
                config={{
                  xAxisKey: result.intent.dimensions[0],
                  yAxisKeys: result.intent.measures,
                  showLegend: true,
                  showGrid: true,
                }}
              />
            </div>
          ) : (
            <DataTable
              data={result.data.rows}
              columns={result.data.columns.map(col => ({
                key: col,
                label: formatColumnLabel(col),
                align: isNumericColumn(col, result.intent) ? 'right' : 'left',
              }))}
            />
          )}
        </CardContent>
      </Card>
      
      {/* SQL Query (Collapsed) */}
      <details className="group">
        <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
          View generated SQL
        </summary>
        <div className="mt-2">
          <CodeBlock language="sql" code={result.sql} />
        </div>
      </details>
    </div>
  )
}

function getSuggestedChartType(intent) {
  if (intent.query_type === 'trend') return 'line_chart'
  if (intent.query_type === 'comparison') return 'bar_chart'
  if (intent.dimensions.length === 1 && intent.measures.length === 1) {
    return 'pie_chart'
  }
  return 'bar_chart'
}

function transformDataForChart(data) {
  return data.rows.map(row => {
    const obj = {}
    data.columns.forEach((col, i) => {
      obj[col] = row[i]
    })
    return obj
  })
}
```

### Query Suggestions

```tsx
// src/features/query/components/QuerySuggestions.tsx
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

const DEFAULT_SUGGESTIONS = [
  "What were the total sales by region last month?",
  "Show me the top 10 products by revenue",
  "Compare Q1 vs Q2 sales performance",
  "What is the average order value by customer segment?",
  "Show monthly revenue trend for the past year",
]

export function QuerySuggestions({ onSelect }) {
  const { data: personalSuggestions } = useQuery({
    queryKey: ['query-suggestions'],
    queryFn: () => api.get('/assistant/suggestions').then(r => r.data),
  })
  
  const suggestions = personalSuggestions?.length 
    ? personalSuggestions 
    : DEFAULT_SUGGESTIONS
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Try asking...</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {suggestions.map((suggestion, i) => (
            <Button
              key={i}
              variant="outline"
              className="text-left h-auto py-2"
              onClick={() => onSelect(suggestion)}
            >
              {suggestion}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
```

### Query Loading State

```tsx
// src/features/query/components/QueryLoadingState.tsx
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function QueryLoadingState() {
  return (
    <Card>
      <CardContent className="py-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="flex space-x-2">
            <div className="w-3 h-3 bg-primary rounded-full animate-bounce" />
            <div className="w-3 h-3 bg-primary rounded-full animate-bounce delay-100" />
            <div className="w-3 h-3 bg-primary rounded-full animate-bounce delay-200" />
          </div>
          <p className="text-muted-foreground">Analyzing your question...</p>
        </div>
      </CardContent>
    </Card>
  )
}
```

## Expected Output

```
frontend/src/features/query/
├── components/
│   ├── QueryResult.tsx
│   ├── QuerySuggestions.tsx
│   ├── QueryHistory.tsx
│   ├── QueryLoadingState.tsx
│   ├── QueryError.tsx
│   └── SaveToDashboardDialog.tsx
├── pages/
│   └── QueryPage.tsx
├── hooks/
│   └── useQueryHistory.ts
└── index.ts
```

## Acceptance Criteria

- [ ] Query input accepts natural language
- [ ] Results display as chart and table
- [ ] SQL is shown but collapsed
- [ ] Suggestions help users get started
- [ ] History shows previous queries
- [ ] Results can be saved to dashboard
- [ ] Loading state is informative
- [ ] Error messages are helpful
- [ ] Keyboard shortcuts work (Cmd+Enter)

## Reference Documents

- [NL-to-SQL](./023-nl-to-sql.md)
- [Chart Components](./026-chart-components.md)
