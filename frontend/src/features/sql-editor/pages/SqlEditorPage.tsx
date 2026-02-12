/**
 * SQL Editor Page
 * Full-featured SQL editor with schema explorer, saved queries panel, and results view
 */

import { useState, useCallback, useId, Suspense } from 'react'
import { formatDistanceToNow } from 'date-fns'
import {
  Database,
  AlertCircle,
  Loader2,
  Save,
  Zap,
  ChevronLeft,
  ChevronRight,
  FileCode,
  Search,
  MoreVertical,
  Pencil,
  Trash2,
  Copy,
  Play,
  Globe,
  Lock,
  Check,
} from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { SQLEditor } from '../components/SQLEditor'
import { SQLResultsChart } from '../components/SQLResultsChart'
import { SchemaExplorer } from '../components/SchemaExplorer'
import { QueryTabs } from '../components/QueryTabs'
import { useSqlQuery } from '../hooks/useSqlQuery'
import { useSchemaExplorer } from '../hooks/useSchemaExplorer'
import { useTenantClickHouseInfo, useTenantClickHouseSchema } from '../hooks/useTenantClickHouse'
import { useSavedQueries, useCreateSavedQuery, useUpdateSavedQuery, useDeleteSavedQuery } from '../hooks/useSavedQueries'
import { useDataSources } from '@/features/datasources/hooks/useDataSources'
import type { QueryTab, DatasourceOption, SavedQuery } from '../types'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/ui/use-toast'

const TENANT_CLICKHOUSE_ID = '__tenant_clickhouse__'

const QUERY_TYPE_CONFIG = {
  adhoc: { label: 'Ad-hoc', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' },
  pyspark: { label: 'PySpark', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' },
  dbt: { label: 'dbt', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  report: { label: 'Report', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
}

export function SqlEditorPage() {
  const newTabId = useId()
  const { toast } = useToast()
  
  // State
  const [selectedDatasourceId, setSelectedDatasourceId] = useState<string>('')
  const [isClickhouse, setIsClickhouse] = useState(false)
  const [tabs, setTabs] = useState<QueryTab[]>([
    { id: newTabId, name: 'Query 1', sql: '' },
  ])
  const [activeTabId, setActiveTabId] = useState(newTabId)
  const [queryLimit, setQueryLimit] = useState(200)
  
  // Panel states
  const [savedQueriesPanelOpen, setSavedQueriesPanelOpen] = useState(true)
  const [schemaExplorerPanelOpen, setSchemaExplorerPanelOpen] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('all')
  
  // Save dialog state
  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveDescription, setSaveDescription] = useState('')
  const [saveQueryType, setSaveQueryType] = useState<'adhoc' | 'pyspark' | 'dbt' | 'report'>('adhoc')
  const [saveIsPublic, setSaveIsPublic] = useState(false)
  
  // Delete confirmation
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [queryToDelete, setQueryToDelete] = useState<SavedQuery | null>(null)

  // Get current tab
  const activeTab = tabs.find((t) => t.id === activeTabId) || tabs[0]

  // Fetch datasources
  const { data: datasourcesData, isLoading: datasourcesLoading } = useDataSources()
  const datasources = datasourcesData?.items || []
  
  // Fetch tenant ClickHouse info
  const { data: clickhouseInfo } = useTenantClickHouseInfo()
  
  // Fetch saved queries
  const { data: savedQueriesData, isLoading: savedQueriesLoading } = useSavedQueries()
  const savedQueries = savedQueriesData?.items || []
  
  // Mutations
  const createSavedQuery = useCreateSavedQuery()
  const updateSavedQuery = useUpdateSavedQuery()
  const deleteSavedQuery = useDeleteSavedQuery()

  // Filter saved queries
  const filteredQueries = savedQueries.filter((query) => {
    const matchesSearch =
      searchQuery === '' ||
      query.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      query.description?.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesType = selectedTypeFilter === 'all' || query.query_type === selectedTypeFilter
    
    return matchesSearch && matchesType
  })

  // Combine datasources with tenant ClickHouse
  const allDatasources: DatasourceOption[] = [
    ...(clickhouseInfo ? [{
      id: TENANT_CLICKHOUSE_ID,
      name: clickhouseInfo.name,
      db_type: 'clickhouse',
      status: 'active',
      is_tenant_clickhouse: true,
    }] : []),
    ...datasources.map(ds => ({
      id: ds.id,
      name: ds.name,
      db_type: ds.db_type,
      status: ds.status,
      is_tenant_clickhouse: false,
    })),
  ]

  // Get the actual connection ID for schema explorer
  const schemaConnectionId = isClickhouse ? undefined : selectedDatasourceId

  // Schema explorer for regular connections
  const {
    schemas: connectionSchemas,
    isLoading: connectionSchemaLoading,
    error: connectionSchemaError,
    refetch: refetchConnectionSchema,
  } = useSchemaExplorer(schemaConnectionId)

  // Schema explorer for tenant ClickHouse
  const {
    data: clickhouseSchemas,
    isLoading: clickhouseSchemaLoading,
    error: clickhouseSchemaError,
    refetch: refetchClickhouseSchema,
  } = useTenantClickHouseSchema(isClickhouse)

  // Combine schemas based on selection
  const schemas = isClickhouse ? (clickhouseSchemas || []) : connectionSchemas
  const schemaLoading = isClickhouse ? clickhouseSchemaLoading : connectionSchemaLoading
  const schemaError = isClickhouse 
    ? (clickhouseSchemaError?.message || null) 
    : connectionSchemaError
  const refetchSchema = isClickhouse ? refetchClickhouseSchema : refetchConnectionSchema

  // SQL query execution
  const { execute, result, error, isLoading: queryLoading } = useSqlQuery()

  // Handle datasource selection
  const handleDatasourceChange = useCallback((value: string) => {
    setSelectedDatasourceId(value)
    setIsClickhouse(value === TENANT_CLICKHOUSE_ID)
  }, [])

  // Update tab SQL
  const updateTabSql = useCallback((sql: string) => {
    setTabs((prev) =>
      prev.map((tab) =>
        tab.id === activeTabId ? { ...tab, sql, isDirty: true } : tab
      )
    )
  }, [activeTabId])

  // Execute query
  const handleExecute = useCallback(() => {
    if (!selectedDatasourceId || !activeTab.sql.trim()) return

    setTabs((prev) =>
      prev.map((tab) =>
        tab.id === activeTabId ? { ...tab, isExecuting: true } : tab
      )
    )

    execute({
      sql: activeTab.sql,
      datasourceId: isClickhouse ? undefined : selectedDatasourceId,
      isClickhouse,
      limit: queryLimit,
    })

    setTimeout(() => {
      setTabs((prev) =>
        prev.map((tab) =>
          tab.id === activeTabId ? { ...tab, isExecuting: false } : tab
        )
      )
    }, 0)
  }, [selectedDatasourceId, activeTab, activeTabId, execute, isClickhouse, queryLimit])

  // Open save dialog - pre-fill if editing existing query
  const handleOpenSaveDialog = useCallback(() => {
    if (activeTab.savedQueryId) {
      // Editing existing query - find it
      const existingQuery = savedQueries.find(q => q.id === activeTab.savedQueryId)
      if (existingQuery) {
        setSaveName(existingQuery.name)
        setSaveDescription(existingQuery.description || '')
        setSaveQueryType(existingQuery.query_type)
        setSaveIsPublic(existingQuery.is_public)
      }
    } else {
      // New query
      setSaveName(activeTab.name !== `Query ${tabs.indexOf(activeTab) + 1}` ? activeTab.name : '')
      setSaveDescription('')
      setSaveQueryType('adhoc')
      setSaveIsPublic(false)
    }
    setSaveDialogOpen(true)
  }, [activeTab, savedQueries, tabs])

  // Save or update query handler
  const handleSaveQuery = useCallback(async () => {
    if (!saveName.trim() || !activeTab.sql.trim()) return
    
    try {
      if (activeTab.savedQueryId) {
        // Update existing query
        await updateSavedQuery.mutateAsync({
          id: activeTab.savedQueryId,
          name: saveName,
          description: saveDescription,
          sql: activeTab.sql,
          query_type: saveQueryType,
          is_public: saveIsPublic,
        })
        
        toast({
          title: 'Query updated',
          description: `"${saveName}" has been updated successfully.`,
        })
      } else {
        // Create new query
        const newQuery = await createSavedQuery.mutateAsync({
          name: saveName,
          description: saveDescription,
          sql: activeTab.sql,
          connection_id: isClickhouse ? undefined : selectedDatasourceId,
          is_clickhouse: isClickhouse,
          query_type: saveQueryType,
          is_public: saveIsPublic,
        })
        
        // Update tab with savedQueryId
        setTabs((prev) =>
          prev.map((tab) =>
            tab.id === activeTabId 
              ? { ...tab, savedQueryId: newQuery.id, name: saveName, isDirty: false } 
              : tab
          )
        )
        
        toast({
          title: 'Query saved',
          description: `"${saveName}" has been saved successfully.`,
        })
      }
      
      setSaveDialogOpen(false)
      setSaveName('')
      setSaveDescription('')
      setSaveQueryType('adhoc')
      setSaveIsPublic(false)
      
      // Mark tab as not dirty
      setTabs((prev) =>
        prev.map((tab) =>
          tab.id === activeTabId ? { ...tab, isDirty: false, name: saveName } : tab
        )
      )
    } catch (err) {
      console.error('Failed to save query:', err)
      toast({
        title: 'Error',
        description: 'Failed to save query. Please try again.',
        variant: 'destructive',
      })
    }
  }, [saveName, saveDescription, activeTab, isClickhouse, selectedDatasourceId, createSavedQuery, updateSavedQuery, activeTabId, saveQueryType, saveIsPublic, toast])

  // Edit saved query - open in new tab
  const handleEditSavedQuery = useCallback((query: SavedQuery) => {
    // Check if query is already open in a tab
    const existingTab = tabs.find(t => t.savedQueryId === query.id)
    if (existingTab) {
      setActiveTabId(existingTab.id)
      return
    }
    
    // Create new tab with the query
    const newId = `tab-${Date.now()}`
    const newTab: QueryTab = {
      id: newId,
      name: query.name,
      sql: query.sql,
      savedQueryId: query.id,
      datasourceId: query.connection_id || undefined,
      isClickhouse: query.is_clickhouse,
      isDirty: false,
    }
    
    setTabs((prev) => [...prev, newTab])
    setActiveTabId(newId)
    
    // Set the correct datasource
    if (query.is_clickhouse) {
      handleDatasourceChange(TENANT_CLICKHOUSE_ID)
    } else if (query.connection_id) {
      handleDatasourceChange(query.connection_id)
    }
  }, [tabs, handleDatasourceChange])

  // Delete saved query
  const handleDeleteQuery = useCallback(async () => {
    if (!queryToDelete) return
    
    try {
      await deleteSavedQuery.mutateAsync(queryToDelete.id)
      
      // Close any tabs that have this query
      setTabs((prev) => {
        const filtered = prev.filter(t => t.savedQueryId !== queryToDelete.id)
        if (filtered.length === 0) {
          // Add a new empty tab if all tabs were closed
          return [{ id: `tab-${Date.now()}`, name: 'Query 1', sql: '' }]
        }
        return filtered
      })
      
      toast({
        title: 'Query deleted',
        description: `"${queryToDelete.name}" has been deleted.`,
      })
      
      setDeleteDialogOpen(false)
      setQueryToDelete(null)
    } catch (err) {
      console.error('Failed to delete query:', err)
      toast({
        title: 'Error',
        description: 'Failed to delete query. Please try again.',
        variant: 'destructive',
      })
    }
  }, [queryToDelete, deleteSavedQuery, toast])

  // Copy SQL to clipboard
  const handleCopySql = useCallback(async (query: SavedQuery) => {
    try {
      await navigator.clipboard.writeText(query.sql)
      toast({
        title: 'Copied',
        description: 'SQL copied to clipboard.',
      })
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [toast])

  // Handle column click from schema explorer
  const handleColumnClick = useCallback(
    (_tableName: string, columnName: string) => {
      updateTabSql(activeTab.sql + columnName + ' ')
    },
    [activeTab.sql, updateTabSql]
  )

  // Handle table click - insert SELECT * FROM table
  const handleTableClick = useCallback(
    (tableName: string) => {
      const query = `SELECT * FROM ${tableName} LIMIT ${queryLimit}`
      updateTabSql(query)
    },
    [updateTabSql, queryLimit]
  )

  // Handle insert SELECT from schema explorer
  const handleInsertSelect = useCallback(
    (sql: string) => {
      updateTabSql(sql)
    },
    [updateTabSql]
  )

  // Tab management
  const handleNewTab = useCallback(() => {
    const newId = `tab-${Date.now()}`
    const newTab: QueryTab = {
      id: newId,
      name: `Query ${tabs.length + 1}`,
      sql: '',
    }
    setTabs((prev) => [...prev, newTab])
    setActiveTabId(newId)
  }, [tabs.length])

  const handleCloseTab = useCallback(
    (tabId: string) => {
      setTabs((prev) => {
        const filtered = prev.filter((t) => t.id !== tabId)
        if (filtered.length === 0) {
          // Always keep at least one tab
          const newTab: QueryTab = { id: `tab-${Date.now()}`, name: 'Query 1', sql: '' }
          return [newTab]
        }
        if (tabId === activeTabId) {
          setActiveTabId(filtered[filtered.length - 1].id)
        }
        return filtered
      })
    },
    [activeTabId]
  )

  const handleRenameTab = useCallback((tabId: string, name: string) => {
    setTabs((prev) =>
      prev.map((tab) => (tab.id === tabId ? { ...tab, name } : tab))
    )
  }, [])

  return (
    <TooltipProvider>
      <div className="h-[calc(100vh-4rem)] flex flex-col bg-background">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-card">
          <div className="flex items-center gap-3">
            <Database className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">SQL Editor</h1>
          </div>

          <div className="flex items-center gap-2">
            {/* Save button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant={activeTab.savedQueryId ? 'default' : 'outline'} 
                  size="sm" 
                  disabled={!activeTab.sql.trim()}
                  onClick={handleOpenSaveDialog}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {activeTab.savedQueryId ? 'Update' : 'Save'}
                  {activeTab.isDirty && activeTab.savedQueryId && (
                    <span className="w-2 h-2 rounded-full bg-orange-500" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {activeTab.savedQueryId 
                  ? 'Update existing saved query' 
                  : 'Save as new query'}
              </TooltipContent>
            </Tooltip>

            {/* Datasource selector */}
            <Select
              value={selectedDatasourceId}
              onValueChange={handleDatasourceChange}
            >
              <SelectTrigger className="w-[260px]">
                <SelectValue placeholder={datasourcesLoading ? "Loading..." : "Select data source"} />
              </SelectTrigger>
              <SelectContent>
                {allDatasources.length === 0 && !datasourcesLoading ? (
                  <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                    No data sources available.
                  </div>
                ) : (
                  <>
                    {clickhouseInfo && (
                      <>
                        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                          Tenant Analytics
                        </div>
                        <SelectItem value={TENANT_CLICKHOUSE_ID}>
                          <div className="flex items-center gap-2">
                            <Zap className="h-3 w-3 text-orange-500" />
                            <span>{clickhouseInfo.name}</span>
                          </div>
                        </SelectItem>
                        <div className="my-1 border-t" />
                      </>
                    )}
                    
                    {datasources.length > 0 && (
                      <>
                        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                          Connections
                        </div>
                        {datasources.map((ds) => (
                          <SelectItem key={ds.id} value={ds.id}>
                            <div className="flex items-center gap-2">
                              <div
                                className={`w-2 h-2 rounded-full ${
                                  ds.status === 'active' ? 'bg-green-500' : 'bg-gray-400'
                                }`}
                              />
                              <span>{ds.name}</span>
                              <span className="text-xs text-muted-foreground">({ds.db_type})</span>
                            </div>
                          </SelectItem>
                        ))}
                      </>
                    )}
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Query Tabs */}
        <QueryTabs
          tabs={tabs}
          activeTabId={activeTabId}
          onTabChange={setActiveTabId}
          onTabClose={handleCloseTab}
          onNewTab={handleNewTab}
          onTabRename={handleRenameTab}
        />

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Saved Queries Panel - Left */}
          <div 
            className={cn(
              "border-r bg-card transition-all duration-300 flex flex-col",
              savedQueriesPanelOpen ? "w-72" : "w-0"
            )}
          >
            {savedQueriesPanelOpen && (
              <>
                {/* Panel Header */}
                <div className="p-3 border-b">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <FileCode className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium text-sm">Saved Queries</span>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {filteredQueries.length}
                    </Badge>
                  </div>
                  
                  {/* Search */}
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      placeholder="Search queries..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8 h-8 text-sm"
                    />
                  </div>
                  
                  {/* Type Filter */}
                  <Select value={selectedTypeFilter} onValueChange={setSelectedTypeFilter}>
                    <SelectTrigger className="h-8 mt-2 text-xs">
                      <SelectValue placeholder="All types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="adhoc">Ad-hoc</SelectItem>
                      <SelectItem value="pyspark">PySpark</SelectItem>
                      <SelectItem value="dbt">dbt</SelectItem>
                      <SelectItem value="report">Report</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Queries List */}
                <ScrollArea className="flex-1">
                  <div className="p-2 space-y-1">
                    {savedQueriesLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                      </div>
                    ) : filteredQueries.length === 0 ? (
                      <div className="text-center py-8 px-4">
                        <FileCode className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                        <p className="text-sm text-muted-foreground">
                          {searchQuery ? 'No queries match your search' : 'No saved queries yet'}
                        </p>
                      </div>
                    ) : (
                      filteredQueries.map((query) => (
                        <SavedQueryItem
                          key={query.id}
                          query={query}
                          isActive={activeTab.savedQueryId === query.id}
                          onEdit={() => handleEditSavedQuery(query)}
                          onCopy={() => handleCopySql(query)}
                          onDelete={() => {
                            setQueryToDelete(query)
                            setDeleteDialogOpen(true)
                          }}
                        />
                      ))
                    )}
                  </div>
                </ScrollArea>
              </>
            )}
          </div>

          {/* Toggle Panel Button */}
          <button
            onClick={() => setSavedQueriesPanelOpen(!savedQueriesPanelOpen)}
            className="w-5 flex-shrink-0 bg-muted/50 hover:bg-muted border-r flex items-center justify-center transition-colors"
          >
            {savedQueriesPanelOpen ? (
              <ChevronLeft className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>

          {/* Editor Area */}
          {!selectedDatasourceId ? (
            <div className="flex-1 flex items-center justify-center">
              <Alert className="max-w-md">
                <Database className="h-4 w-4" />
                <AlertDescription>
                  Select a data source to start writing SQL queries.
                </AlertDescription>
              </Alert>
            </div>
          ) : (
            <div className="flex-1 flex overflow-hidden">
              {/* Schema Explorer - Collapsible */}
              <div 
                className={cn(
                  "border-r flex-shrink-0 overflow-hidden bg-card transition-all duration-300",
                  schemaExplorerPanelOpen ? "w-72" : "w-0"
                )}
              >
                {schemaExplorerPanelOpen && (
                  <SchemaExplorer
                    schemas={schemas}
                    isLoading={schemaLoading}
                    error={schemaError}
                    onRefresh={() => refetchSchema()}
                    onColumnClick={handleColumnClick}
                    onTableClick={handleTableClick}
                    onInsertSelect={handleInsertSelect}
                    className="h-full"
                  />
                )}
              </div>
              
              {/* Toggle Schema Explorer Button */}
              <button
                onClick={() => setSchemaExplorerPanelOpen(!schemaExplorerPanelOpen)}
                className="w-5 flex-shrink-0 bg-muted/50 hover:bg-muted border-r flex items-center justify-center transition-colors"
                title={schemaExplorerPanelOpen ? "Collapse schema explorer" : "Expand schema explorer"}
              >
                {schemaExplorerPanelOpen ? (
                  <ChevronLeft className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </button>

              {/* Editor and Results */}
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* SQL Editor */}
                <div className="h-2/5 min-h-[200px] border-b">
                  <Suspense fallback={
                    <div className="flex items-center justify-center h-full">
                      <Loader2 className="h-6 w-6 animate-spin" />
                    </div>
                  }>
                    <SQLEditor
                      value={activeTab.sql}
                      onChange={updateTabSql}
                      onExecute={handleExecute}
                      isExecuting={queryLoading}
                      executionTime={result?.executionTimeMs}
                      rowCount={result?.rowCount}
                      schemas={schemas}
                      queryLimit={queryLimit}
                      onQueryLimitChange={setQueryLimit}
                      className="h-full"
                    />
                  </Suspense>
                </div>

                {/* Results */}
                <div className="flex-1 overflow-hidden bg-card">
                  {error ? (
                    <div className="p-4">
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          <pre className="mt-2 text-sm whitespace-pre-wrap">{error}</pre>
                        </AlertDescription>
                      </Alert>
                    </div>
                  ) : result ? (
                    <SQLResultsChart result={result} sqlQuery={activeTab.sql} className="h-full" />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                      <Play className="h-8 w-8" />
                      <p>Run a query to see results</p>
                      <p className="text-xs">Press Ctrl+Enter or click Run</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Save Dialog */}
        <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>
                {activeTab.savedQueryId ? 'Update Query' : 'Save Query'}
              </DialogTitle>
              <DialogDescription>
                {activeTab.savedQueryId 
                  ? 'Update the saved query with your changes.'
                  : 'Save this query for later use in PySpark or dbt builders.'}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="e.g., Active Users Query"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={saveDescription}
                  onChange={(e) => setSaveDescription(e.target.value)}
                  placeholder="What does this query do?"
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="queryType">Type</Label>
                  <Select
                    value={saveQueryType}
                    onValueChange={(v) => setSaveQueryType(v as 'adhoc' | 'pyspark' | 'dbt' | 'report')}
                  >
                    <SelectTrigger id="queryType">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="adhoc">Ad-hoc</SelectItem>
                      <SelectItem value="pyspark">PySpark</SelectItem>
                      <SelectItem value="dbt">dbt Model</SelectItem>
                      <SelectItem value="report">Report</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Visibility</Label>
                  <Button
                    type="button"
                    variant={saveIsPublic ? 'default' : 'outline'}
                    className="w-full justify-start gap-2"
                    onClick={() => setSaveIsPublic(!saveIsPublic)}
                  >
                    {saveIsPublic ? (
                      <>
                        <Globe className="h-4 w-4" />
                        Public
                      </>
                    ) : (
                      <>
                        <Lock className="h-4 w-4" />
                        Private
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleSaveQuery} 
                disabled={!saveName.trim() || createSavedQuery.isPending || updateSavedQuery.isPending}
              >
                {(createSavedQuery.isPending || updateSavedQuery.isPending) ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    {activeTab.savedQueryId ? 'Update' : 'Save'}
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Query</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete "{queryToDelete?.name}"? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteQuery}
                disabled={deleteSavedQuery.isPending}
              >
                {deleteSavedQuery.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  )
}

/** Individual saved query item in the panel */
interface SavedQueryItemProps {
  query: SavedQuery
  isActive: boolean
  onEdit: () => void
  onCopy: () => void
  onDelete: () => void
}

function SavedQueryItem({ query, isActive, onEdit, onCopy, onDelete }: SavedQueryItemProps) {
  const typeConfig = QUERY_TYPE_CONFIG[query.query_type] || QUERY_TYPE_CONFIG.adhoc

  return (
    <div
      className={cn(
        "group relative p-2.5 rounded-lg border cursor-pointer transition-all",
        "hover:bg-accent hover:border-accent-foreground/20",
        isActive && "bg-primary/10 border-primary/30"
      )}
      onClick={onEdit}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="font-medium text-sm truncate">{query.name}</span>
            {isActive && (
              <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                Open
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0", typeConfig.color)}>
              {typeConfig.label}
            </Badge>
            {query.is_clickhouse && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                <Zap className="h-2.5 w-2.5 mr-0.5" />
                CH
              </Badge>
            )}
            {query.is_public ? (
              <Globe className="h-3 w-3 text-muted-foreground" />
            ) : (
              <Lock className="h-3 w-3 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Actions Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreVertical className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }}>
              <Pencil className="h-3.5 w-3.5 mr-2" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onCopy(); }}>
              <Copy className="h-3.5 w-3.5 mr-2" />
              Copy SQL
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="h-3.5 w-3.5 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* SQL Preview */}
      <pre className="mt-2 text-[10px] bg-muted/50 p-1.5 rounded text-muted-foreground font-mono truncate">
        {query.sql.substring(0, 60)}{query.sql.length > 60 ? '...' : ''}
      </pre>

      {/* Footer */}
      <div className="mt-1.5 text-[10px] text-muted-foreground">
        {query.updated_at
          ? formatDistanceToNow(new Date(query.updated_at), { addSuffix: true })
          : 'Unknown'}
      </div>
    </div>
  )
}
