/**
 * Saved Queries List Component
 * Displays a list of saved queries for the authenticated tenant
 */

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import {
  FileCode,
  Search,
  MoreVertical,
  Pencil,
  Trash2,
  Copy,
  Play,
  Filter,
  Globe,
  Lock,
  Loader2,
  Database,
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useSavedQueries, useUpdateSavedQuery, useDeleteSavedQuery } from '../hooks/useSavedQueries'
import type { SavedQuery } from '../types'
import { cn } from '@/lib/utils'

interface SavedQueriesListProps {
  /** Callback when a query is selected to run */
  onRunQuery?: (query: SavedQuery) => void
  /** View mode: grid or table */
  viewMode?: 'grid' | 'table'
  /** Filter by query type */
  queryTypeFilter?: 'adhoc' | 'pyspark' | 'dbt' | 'report'
}

const QUERY_TYPE_CONFIG = {
  adhoc: { label: 'Ad-hoc', color: 'bg-gray-100 text-gray-700' },
  pyspark: { label: 'PySpark', color: 'bg-orange-100 text-orange-700' },
  dbt: { label: 'dbt', color: 'bg-green-100 text-green-700' },
  report: { label: 'Report', color: 'bg-blue-100 text-blue-700' },
}

export function SavedQueriesList({
  onRunQuery,
  viewMode = 'grid',
  queryTypeFilter,
}: SavedQueriesListProps) {
  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>(queryTypeFilter || 'all')
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedQuery, setSelectedQuery] = useState<SavedQuery | null>(null)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [currentView, setCurrentView] = useState<'grid' | 'table'>(viewMode)

  // Fetch saved queries with optional filter
  const {
    data: savedQueriesData,
    isLoading,
    error,
    refetch,
  } = useSavedQueries(
    selectedType !== 'all' ? { query_type: selectedType as SavedQuery['query_type'] } : undefined
  )

  const updateSavedQuery = useUpdateSavedQuery()
  const deleteSavedQuery = useDeleteSavedQuery()

  const savedQueries = savedQueriesData?.items || []

  // Filter queries by search
  const filteredQueries = savedQueries.filter((query) => {
    const matchesSearch =
      searchQuery === '' ||
      query.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      query.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      query.sql.toLowerCase().includes(searchQuery.toLowerCase()) ||
      query.tags?.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))

    return matchesSearch
  })

  // Handlers
  const handleEditClick = (query: SavedQuery) => {
    setSelectedQuery(query)
    setEditName(query.name)
    setEditDescription(query.description || '')
    setEditDialogOpen(true)
  }

  const handleDeleteClick = (query: SavedQuery) => {
    setSelectedQuery(query)
    setDeleteDialogOpen(true)
  }

  const handleEditSave = async () => {
    if (!selectedQuery) return

    try {
      await updateSavedQuery.mutateAsync({
        id: selectedQuery.id,
        name: editName,
        description: editDescription,
      })
      setEditDialogOpen(false)
      setSelectedQuery(null)
    } catch (err) {
      console.error('Failed to update query:', err)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!selectedQuery) return

    try {
      await deleteSavedQuery.mutateAsync(selectedQuery.id)
      setDeleteDialogOpen(false)
      setSelectedQuery(null)
    } catch (err) {
      console.error('Failed to delete query:', err)
    }
  }

  const handleCopySQL = async (query: SavedQuery) => {
    try {
      await navigator.clipboard.writeText(query.sql)
    } catch (err) {
      console.error('Failed to copy SQL:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Failed to load saved queries</p>
        <Button variant="outline" onClick={() => refetch()} className="mt-4">
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header and Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search queries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Select value={selectedType} onValueChange={setSelectedType}>
            <SelectTrigger className="w-[140px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="adhoc">Ad-hoc</SelectItem>
              <SelectItem value="pyspark">PySpark</SelectItem>
              <SelectItem value="dbt">dbt</SelectItem>
              <SelectItem value="report">Report</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center border rounded-md">
            <Button
              variant={currentView === 'grid' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setCurrentView('grid')}
              className="rounded-r-none"
            >
              Grid
            </Button>
            <Button
              variant={currentView === 'table' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setCurrentView('table')}
              className="rounded-l-none"
            >
              Table
            </Button>
          </div>
        </div>
      </div>

      {/* Results count */}
      <p className="text-sm text-muted-foreground">
        {filteredQueries.length} {filteredQueries.length === 1 ? 'query' : 'queries'} found
      </p>

      {/* Empty state */}
      {filteredQueries.length === 0 && (
        <div className="text-center py-12 bg-muted/30 rounded-lg">
          <FileCode className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-medium text-lg">No saved queries</h3>
          <p className="text-muted-foreground mt-1">
            {searchQuery
              ? 'No queries match your search criteria'
              : 'Save queries from the SQL Editor to see them here'}
          </p>
        </div>
      )}

      {/* Grid View */}
      {currentView === 'grid' && filteredQueries.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredQueries.map((query) => (
            <SavedQueryCard
              key={query.id}
              query={query}
              onEdit={() => handleEditClick(query)}
              onDelete={() => handleDeleteClick(query)}
              onCopy={() => handleCopySQL(query)}
              onRun={onRunQuery ? () => onRunQuery(query) : undefined}
            />
          ))}
        </div>
      )}

      {/* Table View */}
      {currentView === 'table' && filteredQueries.length > 0 && (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Visibility</TableHead>
                <TableHead>Tags</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredQueries.map((query) => (
                <TableRow key={query.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{query.name}</p>
                      {query.description && (
                        <p className="text-sm text-muted-foreground truncate max-w-xs">
                          {query.description}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn('text-xs', QUERY_TYPE_CONFIG[query.query_type]?.color)}
                    >
                      {QUERY_TYPE_CONFIG[query.query_type]?.label || query.query_type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {query.is_public ? (
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Globe className="h-3 w-3" />
                        <span className="text-xs">Public</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Lock className="h-3 w-3" />
                        <span className="text-xs">Private</span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap max-w-[150px]">
                      {query.tags?.slice(0, 2).map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                      {query.tags?.length > 2 && (
                        <Badge variant="secondary" className="text-xs">
                          +{query.tags.length - 2}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {query.updated_at
                      ? formatDistanceToNow(new Date(query.updated_at), { addSuffix: true })
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {onRunQuery && (
                          <>
                            <DropdownMenuItem onClick={() => onRunQuery(query)}>
                              <Play className="h-4 w-4 mr-2" />
                              Run Query
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                          </>
                        )}
                        <DropdownMenuItem onClick={() => handleCopySQL(query)}>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy SQL
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleEditClick(query)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => handleDeleteClick(query)}
                          className="text-destructive"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Query</DialogTitle>
            <DialogDescription>Update the name and description of your saved query.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Name</Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Query name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Optional description"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleEditSave}
              disabled={!editName.trim() || updateSavedQuery.isPending}
            >
              {updateSavedQuery.isPending ? 'Saving...' : 'Save Changes'}
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
              Are you sure you want to delete "{selectedQuery?.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteSavedQuery.isPending}
            >
              {deleteSavedQuery.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

/** Individual query card component */
interface SavedQueryCardProps {
  query: SavedQuery
  onEdit: () => void
  onDelete: () => void
  onCopy: () => void
  onRun?: () => void
}

function SavedQueryCard({ query, onEdit, onDelete, onCopy, onRun }: SavedQueryCardProps) {
  const typeConfig = QUERY_TYPE_CONFIG[query.query_type] || QUERY_TYPE_CONFIG.adhoc

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <FileCode className="h-5 w-5 text-primary" />
          </div>
          <div className="space-y-1 min-w-0 flex-1">
            <h3 className="font-semibold text-sm truncate">{query.name}</h3>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={cn('text-xs', typeConfig.color)}>
                {typeConfig.label}
              </Badge>
              {query.is_clickhouse && (
                <Badge variant="outline" className="text-xs">
                  <Database className="h-3 w-3 mr-1" />
                  ClickHouse
                </Badge>
              )}
            </div>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {onRun && (
              <>
                <DropdownMenuItem onClick={onRun}>
                  <Play className="h-4 w-4 mr-2" />
                  Run Query
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem onClick={onCopy}>
              <Copy className="h-4 w-4 mr-2" />
              Copy SQL
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onEdit}>
              <Pencil className="h-4 w-4 mr-2" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onDelete} className="text-destructive">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent className="pt-0">
        {query.description && (
          <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{query.description}</p>
        )}

        {/* SQL Preview */}
        <pre className="text-xs bg-muted p-2 rounded overflow-hidden text-ellipsis whitespace-nowrap font-mono">
          {query.sql.substring(0, 80)}
          {query.sql.length > 80 ? '...' : ''}
        </pre>

        {/* Tags */}
        {query.tags && query.tags.length > 0 && (
          <div className="flex gap-1 flex-wrap mt-3">
            {query.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {query.tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{query.tags.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            {query.is_public ? (
              <>
                <Globe className="h-3 w-3" />
                <span>Public</span>
              </>
            ) : (
              <>
                <Lock className="h-3 w-3" />
                <span>Private</span>
              </>
            )}
          </div>
          <span>
            {query.updated_at
              ? formatDistanceToNow(new Date(query.updated_at), { addSuffix: true })
              : 'Unknown'}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
