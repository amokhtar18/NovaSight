# Dashboard & Analytics Agent

## ⚙️ Configuration

```yaml
preferred_model: sonnet 4.5
required_tools:
  - read_file
  - create_file
  - replace_string_in_file
  - list_dir
  - file_search
  - grep_search
  - semantic_search
  - fetch_webpage
```

## 🎯 Role

You are the **Dashboard & Analytics Agent** for NovaSight. You handle dashboard creation, chart components, SQL editor, and data visualization.

## 🧠 Expertise

- React data visualization
- SQL query building
- Chart configuration
- Dashboard layouts
- Export functionality
- Real-time updates

## 📋 Component Ownership

**Components 11 & 12: Analytics & Dashboards**
- Query execution API
- Chart configuration service
- Dashboard CRUD API
- Widget management
- Export service
- SQL Editor component
- Chart builder
- Dashboard canvas

## 📁 Project Structure

```
backend/app/
├── api/v1/
│   ├── analytics.py
│   └── dashboards.py
├── services/
│   ├── query_service.py
│   ├── chart_service.py
│   ├── dashboard_service.py
│   └── export_service.py
├── schemas/
│   ├── query_schemas.py
│   ├── chart_schemas.py
│   └── dashboard_schemas.py
└── models/
    ├── dashboard.py
    └── widget.py

frontend/src/
├── pages/analytics/
│   ├── QueryEditorPage.tsx
│   ├── ChartBuilderPage.tsx
│   ├── DashboardsListPage.tsx
│   └── DashboardViewPage.tsx
├── components/analytics/
│   ├── SQLEditor/
│   │   ├── SQLEditor.tsx
│   │   ├── SchemaExplorer.tsx
│   │   ├── QueryHistory.tsx
│   │   └── ResultsTable.tsx
│   ├── Charts/
│   │   ├── ChartContainer.tsx
│   │   ├── BarChart.tsx
│   │   ├── LineChart.tsx
│   │   ├── PieChart.tsx
│   │   ├── AreaChart.tsx
│   │   ├── ScatterChart.tsx
│   │   ├── TableChart.tsx
│   │   └── KPICard.tsx
│   └── Dashboard/
│       ├── DashboardCanvas.tsx
│       ├── WidgetWrapper.tsx
│       ├── WidgetConfig.tsx
│       └── DashboardFilters.tsx
├── hooks/
│   ├── useQuery.ts
│   └── useDashboard.ts
└── services/
    ├── queryService.ts
    └── dashboardService.ts
```

## 🔧 Core Implementation

### Query Service
```python
# backend/app/services/query_service.py
from typing import Dict, List, Any, Tuple
from uuid import UUID
import time
from flask import g
from clickhouse_driver import Client
from app.services.sql_validator import SQLValidator
from app.services.rls_service import RLSService
from app.models import QueryHistory
from app.extensions import db

class QueryService:
    """Service for executing SQL queries against ClickHouse."""
    
    def __init__(
        self,
        clickhouse_host: str,
        validator: SQLValidator,
        rls_service: RLSService
    ):
        self.clickhouse_host = clickhouse_host
        self.validator = validator
        self.rls = rls_service
    
    def execute(
        self,
        sql: str,
        model_name: str,
        limit: int = 1000
    ) -> Tuple[List[Dict], Dict]:
        """Execute SQL query with validation and RLS."""
        tenant = g.tenant
        user = g.current_user
        
        # Validate SQL
        is_valid, error = self.validator.validate(sql)
        if not is_valid:
            raise ValueError(f"Invalid SQL: {error}")
        
        # Inject RLS filters
        sql_with_rls = self.rls.inject_filters(sql, model_name, user)
        
        # Add limit if not present
        if 'LIMIT' not in sql_with_rls.upper():
            sql_with_rls = f"{sql_with_rls.rstrip().rstrip(';')} LIMIT {limit}"
        
        # Execute query
        start_time = time.time()
        client = Client(
            host=self.clickhouse_host,
            database=f"tenant_{tenant.slug}"
        )
        
        try:
            result = client.execute(sql_with_rls, with_column_types=True)
            data = result[0] if result else []
            columns = result[1] if len(result) > 1 else []
        except Exception as e:
            self._log_query(sql, None, str(e))
            raise
        
        execution_time = time.time() - start_time
        
        # Format results
        column_names = [col[0] for col in columns]
        rows = [dict(zip(column_names, row)) for row in data]
        
        metadata = {
            'columns': [{'name': col[0], 'type': col[1]} for col in columns],
            'row_count': len(rows),
            'execution_time_ms': int(execution_time * 1000),
            'truncated': len(rows) == limit
        }
        
        # Log query
        self._log_query(sql, metadata)
        
        return rows, metadata
    
    def _log_query(
        self,
        sql: str,
        metadata: Dict = None,
        error: str = None
    ):
        """Log query to history."""
        history = QueryHistory(
            tenant_id=g.tenant.id,
            user_id=g.current_user.id,
            sql=sql,
            execution_time_ms=metadata.get('execution_time_ms') if metadata else None,
            row_count=metadata.get('row_count') if metadata else None,
            error=error,
            status='success' if not error else 'error'
        )
        db.session.add(history)
        db.session.commit()
```

### Chart Configuration Schema
```python
# backend/app/schemas/chart_schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from enum import Enum

class ChartType(str, Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    TABLE = "table"
    KPI = "kpi"

class AggregationType(str, Enum):
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    DISTINCT_COUNT = "distinct_count"

class ColumnMapping(BaseModel):
    source_column: str
    display_name: Optional[str] = None
    aggregation: Optional[AggregationType] = None
    format: Optional[str] = None  # e.g., "currency", "percent", "date"

class ChartConfig(BaseModel):
    chart_type: ChartType
    title: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    # Data source
    model_name: str
    sql_query: str
    
    # Axis configuration
    x_axis: Optional[ColumnMapping] = None
    y_axis: Optional[List[ColumnMapping]] = None
    
    # For pie charts
    category_column: Optional[str] = None
    value_column: Optional[str] = None
    
    # For KPI
    metric_column: Optional[str] = None
    comparison_column: Optional[str] = None
    
    # Styling
    colors: Optional[List[str]] = None
    show_legend: bool = True
    show_grid: bool = True
    
    # Interactivity
    enable_drill_down: bool = False
    drill_down_config: Optional[Dict] = None
    
    @validator('y_axis')
    def validate_y_axis(cls, v, values):
        if values.get('chart_type') in ['bar', 'line', 'area']:
            if not v or len(v) == 0:
                raise ValueError("Y axis required for this chart type")
        return v
```

### Dashboard Service
```python
# backend/app/services/dashboard_service.py
from typing import List, Optional, Dict
from uuid import UUID, uuid4
from flask import g
from app.models import Dashboard, Widget
from app.schemas.dashboard_schemas import DashboardCreate, WidgetCreate
from app.extensions import db

class DashboardService:
    """Service for managing dashboards."""
    
    def list_dashboards(self, shared_only: bool = False) -> List[Dashboard]:
        """List dashboards for current user."""
        query = Dashboard.query.filter_by(tenant_id=g.tenant.id)
        
        if shared_only:
            query = query.filter(Dashboard.is_shared == True)
        else:
            # User's own dashboards + shared
            query = query.filter(
                (Dashboard.owner_id == g.current_user.id) |
                (Dashboard.is_shared == True)
            )
        
        return query.order_by(Dashboard.updated_at.desc()).all()
    
    def get_dashboard(self, dashboard_id: UUID) -> Optional[Dashboard]:
        """Get dashboard with widgets."""
        dashboard = Dashboard.query.filter_by(
            id=dashboard_id,
            tenant_id=g.tenant.id
        ).first()
        
        if not dashboard:
            return None
        
        # Check access
        if dashboard.owner_id != g.current_user.id and not dashboard.is_shared:
            return None
        
        return dashboard
    
    def create_dashboard(self, data: DashboardCreate) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(
            id=uuid4(),
            tenant_id=g.tenant.id,
            owner_id=g.current_user.id,
            name=data.name,
            description=data.description,
            layout=data.layout or {"columns": 12, "rows": []},
            is_shared=False
        )
        db.session.add(dashboard)
        db.session.commit()
        return dashboard
    
    def add_widget(
        self,
        dashboard_id: UUID,
        data: WidgetCreate
    ) -> Widget:
        """Add widget to dashboard."""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            raise ValueError("Dashboard not found")
        
        if dashboard.owner_id != g.current_user.id:
            raise ValueError("Not authorized to modify this dashboard")
        
        widget = Widget(
            id=uuid4(),
            dashboard_id=dashboard_id,
            name=data.name,
            chart_type=data.chart_config.chart_type.value,
            config=data.chart_config.dict(),
            position=data.position
        )
        db.session.add(widget)
        db.session.commit()
        return widget
    
    def update_layout(
        self,
        dashboard_id: UUID,
        layout: Dict
    ) -> Dashboard:
        """Update dashboard layout."""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            raise ValueError("Dashboard not found")
        
        if dashboard.owner_id != g.current_user.id:
            raise ValueError("Not authorized to modify this dashboard")
        
        dashboard.layout = layout
        db.session.commit()
        return dashboard
```

### SQL Editor Component
```typescript
// frontend/src/components/analytics/SQLEditor/SQLEditor.tsx
import React, { useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import { Play, Save, History } from 'lucide-react';
import { useQuery } from '@/hooks/useQuery';
import { ResultsTable } from './ResultsTable';
import { SchemaExplorer } from './SchemaExplorer';

interface SQLEditorProps {
  modelName: string;
  initialQuery?: string;
  onSave?: (query: string, name: string) => void;
}

export function SQLEditor({ modelName, initialQuery = '', onSave }: SQLEditorProps) {
  const [sql, setSql] = useState(initialQuery);
  const { execute, data, metadata, isLoading, error } = useQuery();
  
  const handleExecute = useCallback(() => {
    if (!sql.trim()) return;
    execute({ sql, modelName });
  }, [sql, modelName, execute]);
  
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleExecute();
    }
  }, [handleExecute]);
  
  return (
    <div className="flex h-full">
      {/* Schema Explorer */}
      <aside className="w-64 border-r bg-muted/30 overflow-auto">
        <SchemaExplorer 
          modelName={modelName}
          onColumnClick={(column) => {
            setSql((prev) => prev + column);
          }}
        />
      </aside>
      
      {/* Editor & Results */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center gap-2 p-2 border-b">
          <Button 
            onClick={handleExecute} 
            disabled={isLoading}
            size="sm"
          >
            <Play className="h-4 w-4 mr-1" />
            Run (Ctrl+Enter)
          </Button>
          
          {onSave && (
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => {
                const name = prompt('Query name:');
                if (name) onSave(sql, name);
              }}
            >
              <Save className="h-4 w-4 mr-1" />
              Save
            </Button>
          )}
          
          {metadata && (
            <span className="text-sm text-muted-foreground ml-auto">
              {metadata.row_count} rows in {metadata.execution_time_ms}ms
              {metadata.truncated && ' (truncated)'}
            </span>
          )}
        </div>
        
        {/* Editor */}
        <div className="h-1/3 min-h-[200px]">
          <Editor
            defaultLanguage="sql"
            value={sql}
            onChange={(value) => setSql(value || '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              automaticLayout: true,
            }}
            onMount={(editor) => {
              editor.addCommand(
                monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
                handleExecute
              );
            }}
          />
        </div>
        
        {/* Results */}
        <div className="flex-1 overflow-auto border-t">
          {error ? (
            <div className="p-4 text-destructive">
              <p className="font-medium">Query Error</p>
              <pre className="mt-2 text-sm">{error}</pre>
            </div>
          ) : data ? (
            <ResultsTable 
              columns={metadata?.columns || []}
              data={data}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Run a query to see results
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

### Chart Container Component
```typescript
// frontend/src/components/analytics/Charts/ChartContainer.tsx
import React, { useMemo } from 'react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ChartConfig } from '@/types/chart';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

interface ChartContainerProps {
  config: ChartConfig;
  data: Record<string, any>[];
  isLoading?: boolean;
}

export function ChartContainer({ config, data, isLoading }: ChartContainerProps) {
  const chartColors = config.colors || COLORS;
  
  const renderChart = useMemo(() => {
    switch (config.chart_type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              {config.show_grid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey={config.x_axis?.source_column} />
              <YAxis />
              <Tooltip />
              {config.show_legend && <Legend />}
              {config.y_axis?.map((y, i) => (
                <Bar
                  key={y.source_column}
                  dataKey={y.source_column}
                  name={y.display_name || y.source_column}
                  fill={chartColors[i % chartColors.length]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );
      
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              {config.show_grid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey={config.x_axis?.source_column} />
              <YAxis />
              <Tooltip />
              {config.show_legend && <Legend />}
              {config.y_axis?.map((y, i) => (
                <Line
                  key={y.source_column}
                  type="monotone"
                  dataKey={y.source_column}
                  name={y.display_name || y.source_column}
                  stroke={chartColors[i % chartColors.length]}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );
      
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data}
                dataKey={config.value_column}
                nameKey={config.category_column}
                cx="50%"
                cy="50%"
                outerRadius={100}
                label
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={chartColors[i % chartColors.length]} />
                ))}
              </Pie>
              <Tooltip />
              {config.show_legend && <Legend />}
            </PieChart>
          </ResponsiveContainer>
        );
      
      case 'area':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data}>
              {config.show_grid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey={config.x_axis?.source_column} />
              <YAxis />
              <Tooltip />
              {config.show_legend && <Legend />}
              {config.y_axis?.map((y, i) => (
                <Area
                  key={y.source_column}
                  type="monotone"
                  dataKey={y.source_column}
                  name={y.display_name || y.source_column}
                  fill={chartColors[i % chartColors.length]}
                  stroke={chartColors[i % chartColors.length]}
                  fillOpacity={0.3}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        );
      
      case 'kpi':
        const value = data[0]?.[config.metric_column || ''];
        const comparison = data[0]?.[config.comparison_column || ''];
        const change = comparison ? ((value - comparison) / comparison * 100) : null;
        
        return (
          <div className="flex flex-col items-center justify-center h-[300px]">
            <span className="text-5xl font-bold">{formatValue(value, config.y_axis?.[0]?.format)}</span>
            {change !== null && (
              <span className={`text-lg mt-2 ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
              </span>
            )}
          </div>
        );
      
      default:
        return <div>Unsupported chart type</div>;
    }
  }, [config, data, chartColors]);
  
  if (isLoading) {
    return (
      <Card>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{config.title}</CardTitle>
        {config.description && (
          <p className="text-sm text-muted-foreground">{config.description}</p>
        )}
      </CardHeader>
      <CardContent>
        {renderChart}
      </CardContent>
    </Card>
  );
}

function formatValue(value: any, format?: string): string {
  if (value === null || value === undefined) return '-';
  
  switch (format) {
    case 'currency':
      return new Intl.NumberFormat('en-US', { 
        style: 'currency', 
        currency: 'USD' 
      }).format(value);
    case 'percent':
      return `${(value * 100).toFixed(1)}%`;
    case 'number':
      return new Intl.NumberFormat('en-US').format(value);
    default:
      return String(value);
  }
}
```

### Dashboard Canvas
```typescript
// frontend/src/components/analytics/Dashboard/DashboardCanvas.tsx
import React, { useState, useCallback } from 'react';
import GridLayout, { Layout } from 'react-grid-layout';
import { ChartContainer } from '../Charts/ChartContainer';
import { WidgetWrapper } from './WidgetWrapper';
import { useDashboard } from '@/hooks/useDashboard';
import { Widget } from '@/types/dashboard';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

interface DashboardCanvasProps {
  dashboardId: string;
  isEditing?: boolean;
}

export function DashboardCanvas({ dashboardId, isEditing = false }: DashboardCanvasProps) {
  const { dashboard, widgets, updateLayout, isLoading } = useDashboard(dashboardId);
  
  const handleLayoutChange = useCallback((newLayout: Layout[]) => {
    if (!isEditing) return;
    
    const layoutMap = newLayout.reduce((acc, item) => ({
      ...acc,
      [item.i]: { x: item.x, y: item.y, w: item.w, h: item.h }
    }), {});
    
    updateLayout(layoutMap);
  }, [isEditing, updateLayout]);
  
  if (isLoading) {
    return <div className="flex items-center justify-center h-full">Loading...</div>;
  }
  
  const layout: Layout[] = widgets.map((widget) => ({
    i: widget.id,
    x: widget.position.x,
    y: widget.position.y,
    w: widget.position.w,
    h: widget.position.h,
    minW: 2,
    minH: 2,
  }));
  
  return (
    <div className="p-4">
      <GridLayout
        className="layout"
        layout={layout}
        cols={12}
        rowHeight={100}
        width={1200}
        onLayoutChange={handleLayoutChange}
        isDraggable={isEditing}
        isResizable={isEditing}
      >
        {widgets.map((widget) => (
          <div key={widget.id}>
            <WidgetWrapper
              widget={widget}
              isEditing={isEditing}
            >
              <ChartContainer
                config={widget.config}
                data={widget.data || []}
                isLoading={widget.isLoading}
              />
            </WidgetWrapper>
          </div>
        ))}
      </GridLayout>
    </div>
  );
}
```

## 📝 Implementation Tasks

### Task 11.1: Query Execution API
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create query endpoint
2. Add SQL validation
3. Integrate RLS injection
4. Add ClickHouse client
5. Create tests

Acceptance Criteria:
- [ ] Queries execute correctly
- [ ] RLS enforced
- [ ] Results returned properly
```

### Task 12.3: Dashboard Canvas
```yaml
Priority: P0
Effort: 4 days

Steps:
1. Implement react-grid-layout
2. Add widget rendering
3. Handle layout persistence
4. Add editing mode
5. Create tests

Acceptance Criteria:
- [ ] Drag and drop works
- [ ] Resize works
- [ ] Layout saves correctly
```

## 🔗 References

- Recharts documentation
- react-grid-layout documentation
- Monaco Editor documentation

---

*Dashboard & Analytics Agent v1.0 - NovaSight Project*
