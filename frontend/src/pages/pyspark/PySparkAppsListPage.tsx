/**
 * PySpark Apps List Page
 * 
 * Displays all PySpark applications with search, filter, and actions.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  Plus, 
  Search, 
  MoreHorizontal, 
  Trash2, 
  Edit, 
  Code, 
  Play,
  AlertCircle,
  CheckCircle,
  Clock,
  FileCode,
  RefreshCw,
  Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/components/ui/use-toast'
import { 
  usePySparkApps, 
  useDeletePySparkApp, 
  useGeneratePySparkCode 
} from '@/features/pyspark/hooks'
import { PySparkApp, PySparkAppStatus, SCDType, WriteMode } from '@/types/pyspark'

// Status badge configurations
const STATUS_CONFIG: Record<PySparkAppStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: React.ReactNode }> = {
  draft: { 
    label: 'Draft', 
    variant: 'secondary', 
    icon: <FileCode className="h-3 w-3" /> 
  },
  active: { 
    label: 'Active', 
    variant: 'default', 
    icon: <CheckCircle className="h-3 w-3" /> 
  },
  inactive: { 
    label: 'Inactive', 
    variant: 'outline', 
    icon: <Clock className="h-3 w-3" /> 
  },
  error: { 
    label: 'Error', 
    variant: 'destructive', 
    icon: <AlertCircle className="h-3 w-3" /> 
  },
}

// SCD type labels
const SCD_LABELS: Record<SCDType, string> = {
  none: 'None',
  type1: 'SCD Type 1',
  type2: 'SCD Type 2',
}

// Write mode labels
const WRITE_MODE_LABELS: Record<WriteMode, string> = {
  overwrite: 'Overwrite',
  append: 'Append',
  merge: 'Merge',
}

export function PySparkAppsListPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedApp, setSelectedApp] = useState<PySparkApp | null>(null)
  
  const { data: appsResponse, isLoading, error, refetch } = usePySparkApps()
  const deleteApp = useDeletePySparkApp()
  const generateCode = useGeneratePySparkCode()
  
  // Filter apps based on search query
  const filteredApps = appsResponse?.apps?.filter((app: PySparkApp) => 
    app.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    app.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    app.source_table?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    app.target_table?.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? []
  
  // Handle delete confirmation
  const handleDeleteClick = (app: PySparkApp) => {
    setSelectedApp(app)
    setDeleteDialogOpen(true)
  }
  
  // Execute delete
  const handleDeleteConfirm = async () => {
    if (!selectedApp) return
    
    try {
      await deleteApp.mutateAsync(selectedApp.id)
      toast({
        title: 'App Deleted',
        description: `Successfully deleted "${selectedApp.name}"`,
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete app. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setDeleteDialogOpen(false)
      setSelectedApp(null)
    }
  }
  
  // Handle generate code
  const handleGenerateCode = async (app: PySparkApp) => {
    try {
      await generateCode.mutateAsync(app.id)
      toast({
        title: 'Code Generated',
        description: `Successfully generated code for "${app.name}"`,
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to generate code. Please try again.',
        variant: 'destructive',
      })
    }
  }
  
  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  
  if (error) {
    return (
      <div className="container py-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <h2 className="text-lg font-semibold mb-2">Error Loading Apps</h2>
            <p className="text-muted-foreground mb-4">
              Failed to load PySpark applications.
            </p>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  return (
    <div className="container py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">PySpark Apps</h1>
          <p className="text-muted-foreground mt-2">
            Manage your PySpark data extraction applications
          </p>
        </div>
        <Button asChild>
          <Link to="/pyspark/new">
            <Plus className="h-4 w-4 mr-2" />
            New PySpark App
          </Link>
        </Button>
      </div>
      
      {/* Search and Filter */}
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search apps by name, description, or table..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
      </Card>
      
      {/* Apps Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredApps.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <FileCode className="h-12 w-12 text-muted-foreground mb-4" />
              <h2 className="text-lg font-semibold mb-2">No PySpark Apps</h2>
              <p className="text-muted-foreground mb-4">
                {searchQuery 
                  ? 'No apps match your search criteria.' 
                  : 'Get started by creating your first PySpark app.'}
              </p>
              {!searchQuery && (
                <Button asChild>
                  <Link to="/pyspark/new">
                    <Plus className="h-4 w-4 mr-2" />
                    Create App
                  </Link>
                </Button>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>SCD Type</TableHead>
                  <TableHead>Write Mode</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredApps.map((app) => {
                  const statusConfig = STATUS_CONFIG[app.status]
                  
                  return (
                    <TableRow key={app.id}>
                      <TableCell>
                        <div>
                          <Link 
                            to={`/pyspark/${app.id}`}
                            className="font-medium hover:underline"
                          >
                            {app.name}
                          </Link>
                          {app.description && (
                            <p className="text-sm text-muted-foreground truncate max-w-[200px]">
                              {app.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {app.source_type === 'table' ? (
                            <span>{app.source_schema}.{app.source_table}</span>
                          ) : (
                            <span className="text-muted-foreground">Custom Query</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {app.target_database && app.target_table ? (
                            <span>{app.target_database}.{app.target_table}</span>
                          ) : (
                            <span className="text-muted-foreground">Not configured</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {SCD_LABELS[app.scd_type]}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">
                          {WRITE_MODE_LABELS[app.write_mode]}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusConfig.variant}>
                          <span className="flex items-center gap-1">
                            {statusConfig.icon}
                            {statusConfig.label}
                          </span>
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {formatDate(app.updated_at)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                              <span className="sr-only">Open menu</span>
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => navigate(`/pyspark/${app.id}`)}>
                              <Code className="h-4 w-4 mr-2" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => navigate(`/pyspark/${app.id}/edit`)}>
                              <Edit className="h-4 w-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleGenerateCode(app)}>
                              <Play className="h-4 w-4 mr-2" />
                              Generate Code
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem 
                              onClick={() => handleDeleteClick(app)}
                              className="text-destructive"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete PySpark App</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{selectedApp?.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteApp.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default PySparkAppsListPage
