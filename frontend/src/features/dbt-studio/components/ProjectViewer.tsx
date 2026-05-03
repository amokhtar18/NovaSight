/**
 * Project Structure Viewer Component
 *
 * Displays the tenant's dbt project file tree with ability to view file contents.
 * Only accessible to super_admin and data_engineer roles.
 */

import { useState, useCallback, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Editor, { loader } from '@monaco-editor/react'
import {
  ChevronRight,
  ChevronDown,
  File,
  Folder,
  FolderOpen,
  Database,
  FileCode,
  FileText,
  RefreshCw,
  Settings,
  Layers,
  Play,
  Trash2,
  Save,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { ScrollArea } from '@/components/ui/scroll-area'
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
import {
  useProjectStructure,
  useFileContent,
  useInitProject,
  useDiscoverSources,
  useGenerateDag,
  useDeleteProjectFile,
  useSaveProjectFile,
} from '../hooks/useDbtStudio'
import type { ProjectNode } from '../services/dbtStudioApi'

// Configure Monaco to load from CDN (matches SQLEditor configuration).
loader.config({
  paths: {
    vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs',
  },
})

// Directories the backend permits editing/deleting in. Keep in sync with
// TenantDbtProjectManager._WRITABLE_ROOT_DIRS / _DELETABLE_ROOT_DIRS.
const EDITABLE_ROOT_DIRS = ['models', 'tests', 'snapshots', 'seeds', 'macros', 'analyses']
const EDITABLE_EXTENSIONS = ['.sql', '.yml', '.yaml', '.md', '.csv', '.sh', '.py']

function isWritablePath(path: string | null): boolean {
  if (!path) return false
  const segments = path.split(/[\\/]/).filter(Boolean)
  if (segments.length === 0 || !EDITABLE_ROOT_DIRS.includes(segments[0])) return false
  const lower = path.toLowerCase()
  return EDITABLE_EXTENSIONS.some((ext) => lower.endsWith(ext))
}

function languageForPath(path: string | null): string {
  if (!path) return 'plaintext'
  const lower = path.toLowerCase()
  if (lower.endsWith('.sql')) return 'sql'
  if (lower.endsWith('.yml') || lower.endsWith('.yaml')) return 'yaml'
  if (lower.endsWith('.md')) return 'markdown'
  if (lower.endsWith('.py')) return 'python'
  if (lower.endsWith('.csv')) return 'plaintext'
  if (lower.endsWith('.sh')) return 'shell'
  if (lower.endsWith('.json')) return 'json'
  return 'plaintext'
}

interface ProjectViewerProps {
  onFileSelect?: (path: string, content: string) => void
}

export function ProjectViewer({ onFileSelect }: ProjectViewerProps) {
  const { toast } = useToast()
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['']))
  const [pendingDelete, setPendingDelete] = useState<ProjectNode | null>(null)

  // Editor state. ``draft`` is the current Monaco buffer; ``baseline`` is
  // the last known on-disk content used to compute the dirty flag.
  const [draft, setDraft] = useState<string>('')
  const [baseline, setBaseline] = useState<string>('')

  // Queries
  const { data: structure, isLoading, refetch } = useProjectStructure()
  const { data: fileData, isLoading: fileLoading } = useFileContent(selectedFile || '', !!selectedFile)

  // Mutations
  const initProject = useInitProject()
  const discoverSources = useDiscoverSources()
  const generateDag = useGenerateDag()
  const deleteFile = useDeleteProjectFile()
  const saveFile = useSaveProjectFile()

  // Directories whose files can be deleted via the API. Must match the
  // backend whitelist in TenantDbtProjectManager._DELETABLE_ROOT_DIRS.
  const DELETABLE_ROOTS = EDITABLE_ROOT_DIRS

  const isDeletable = useCallback((node: ProjectNode): boolean => {
    if (node.type !== 'file') return false
    const segments = node.path.split(/[\\/]/).filter(Boolean)
    return segments.length > 0 && DELETABLE_ROOTS.includes(segments[0])
  }, [DELETABLE_ROOTS])

  // Sync the editor buffer to whichever file is currently loaded. We track
  // both ``draft`` (what's in Monaco) and ``baseline`` (last persisted
  // content) so the Save button can reflect a dirty state.
  useEffect(() => {
    if (fileData?.content !== undefined) {
      setDraft(fileData.content)
      setBaseline(fileData.content)
    } else if (!selectedFile) {
      setDraft('')
      setBaseline('')
    }
  }, [fileData?.content, selectedFile])

  const isEditable = useMemo(() => isWritablePath(selectedFile), [selectedFile])
  const editorLanguage = useMemo(() => languageForPath(selectedFile), [selectedFile])
  const isDirty = isEditable && draft !== baseline

  // Toggle folder expansion
  const toggleFolder = useCallback((path: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }, [])

  // Handle file click
  const handleFileClick = useCallback(
    (path: string) => {
      setSelectedFile(path)
      if (onFileSelect && fileData?.content) {
        onFileSelect(path, fileData.content)
      }
    },
    [onFileSelect, fileData]
  )

  // Initialize project
  const handleInitProject = async () => {
    try {
      await initProject.mutateAsync()
      toast({ title: 'Project initialized successfully' })
      refetch()
    } catch (error) {
      toast({ title: 'Failed to initialize project', variant: 'destructive' })
    }
  }

  // Discover sources
  const handleDiscoverSources = async () => {
    try {
      const result = await discoverSources.mutateAsync()
      toast({
        title: 'Sources discovered',
        description: `Found ${result.tables_discovered} tables in ${result.source_database}`,
      })
      refetch()
    } catch (error) {
      toast({ title: 'Failed to discover sources', variant: 'destructive' })
    }
  }

  // Generate DAG
  const handleGenerateDag = async () => {
    try {
      const result = await generateDag.mutateAsync({
        dag_id: 'daily_run',
        schedule_interval: '0 6 * * *',
        dbt_command: 'build',
        include_test: true,
      })
      toast({
        title: 'DAG generated',
        description: `Created ${result.dag_id}`,
      })
    } catch (error) {
      toast({ title: 'Failed to generate DAG', variant: 'destructive' })
    }
  }

  // Delete a model / test / snapshot / seed / macro / analysis file
  const handleConfirmDelete = async () => {
    if (!pendingDelete) return
    const path = pendingDelete.path
    try {
      const result = await deleteFile.mutateAsync(path)
      toast({
        title: 'File deleted',
        description:
          result.deleted.length > 1
            ? `${pendingDelete.name} and its schema YAML were deleted`
            : `${pendingDelete.name} was deleted`,
      })
      // If the deleted file was open in the viewer, clear it.
      if (selectedFile && result.deleted.includes(selectedFile)) {
        setSelectedFile(null)
      }
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { error?: { message?: string } } } })?.response
          ?.data?.error?.message || 'Failed to delete file'
      toast({ title: 'Delete failed', description: message, variant: 'destructive' })
    } finally {
      setPendingDelete(null)
    }
  }

  // Save the current editor buffer back to the tenant dbt project.
  const handleSave = async () => {
    if (!selectedFile || !isEditable || !isDirty) return
    try {
      await saveFile.mutateAsync({ path: selectedFile, content: draft })
      setBaseline(draft)
      toast({ title: 'File saved', description: selectedFile })
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { error?: { message?: string } } } })?.response
          ?.data?.error?.message || 'Failed to save file'
      toast({ title: 'Save failed', description: message, variant: 'destructive' })
    }
  }

  // Discard local edits and reset the editor to the on-disk baseline.
  const handleDiscard = () => {
    setDraft(baseline)
  }

  // Get icon for file type
  const getFileIcon = (node: ProjectNode) => {
    if (node.type === 'directory') {
      return expandedFolders.has(node.path) ? (
        <FolderOpen className="h-4 w-4 text-yellow-500" />
      ) : (
        <Folder className="h-4 w-4 text-yellow-500" />
      )
    }

    const ext = node.extension?.toLowerCase()
    switch (ext) {
      case '.sql':
        return <Database className="h-4 w-4 text-blue-500" />
      case '.yml':
      case '.yaml':
        return <Settings className="h-4 w-4 text-purple-500" />
      case '.py':
        return <FileCode className="h-4 w-4 text-green-500" />
      case '.md':
        return <FileText className="h-4 w-4 text-gray-500" />
      default:
        return <File className="h-4 w-4 text-gray-400" />
    }
  }

  // Render tree node
  const renderNode = (node: ProjectNode, depth = 0): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path)
    const isSelected = selectedFile === node.path
    const paddingLeft = depth * 16 + 8

    return (
      <div key={node.path}>
        <div
          className={`group flex items-center gap-2 py-1 px-2 rounded cursor-pointer transition-colors ${
            isSelected
              ? 'bg-primary/20 text-primary'
              : 'hover:bg-muted'
          }`}
          style={{ paddingLeft }}
          onClick={() => {
            if (node.type === 'directory') {
              toggleFolder(node.path)
            } else {
              handleFileClick(node.path)
            }
          }}
        >
          {node.type === 'directory' && (
            <span className="w-4">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </span>
          )}
          {node.type !== 'directory' && <span className="w-4" />}
          {getFileIcon(node)}
          <span className="text-sm truncate flex-1">{node.name}</span>
          {node.size !== undefined && (
            <span className="text-xs text-muted-foreground">
              {node.size > 1024 ? `${(node.size / 1024).toFixed(1)}KB` : `${node.size}B`}
            </span>
          )}
          {isDeletable(node) && (
            <button
              type="button"
              aria-label={`Delete ${node.name}`}
              title="Delete"
              className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-1 rounded hover:bg-destructive/10 text-destructive transition-opacity"
              onClick={(e) => {
                e.stopPropagation()
                setPendingDelete(node)
              }}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <AnimatePresence>
          {node.type === 'directory' && isExpanded && node.children && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {node.children.map((child) => renderNode(child, depth + 1))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Project Structure</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-6 w-1/2" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!structure?.exists) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Project Not Initialized</CardTitle>
          <CardDescription>
            The dbt project for your tenant has not been created yet.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Initialize the project to create the dbt project structure and discover source tables
              from your ClickHouse database.
            </p>
            <Button onClick={handleInitProject} disabled={initProject.isPending}>
              {initProject.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Initializing...
                </>
              ) : (
                <>
                  <Layers className="h-4 w-4 mr-2" />
                  Initialize Project
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Project Tree */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Project Structure</CardTitle>
              <CardDescription className="text-xs">
                {structure.tenant_slug}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Database Info */}
          <div className="flex gap-2 mb-4">
            <Badge variant="outline" className="text-xs">
              Source: {structure.source_database}
            </Badge>
            <Badge variant="secondary" className="text-xs">
              Target: {structure.target_database}
            </Badge>
          </div>

          {/* Actions */}
          <div className="flex gap-2 mb-4 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDiscoverSources}
              disabled={discoverSources.isPending}
            >
              <Database className="h-4 w-4 mr-1" />
              Discover Sources
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerateDag}
              disabled={generateDag.isPending}
            >
              <Play className="h-4 w-4 mr-1" />
              Generate DAG
            </Button>
          </div>

          {/* File Tree */}
          <ScrollArea className="h-[400px] border rounded p-2">
            {structure.structure && renderNode(structure.structure)}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* File Content Viewer / Editor */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <CardTitle className="text-lg flex items-center gap-2">
                <span className="truncate">
                  {selectedFile ? selectedFile.split('/').pop() : 'File Viewer'}
                </span>
                {isDirty && (
                  <Badge variant="outline" className="text-xs shrink-0">
                    Unsaved
                  </Badge>
                )}
                {!isEditable && selectedFile && (
                  <Badge variant="secondary" className="text-xs shrink-0">
                    Read-only
                  </Badge>
                )}
              </CardTitle>
              <CardDescription className="text-xs truncate">
                {selectedFile || 'Select a file to view its contents'}
              </CardDescription>
            </div>
            {selectedFile && isEditable && (
              <div className="flex gap-1 shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDiscard}
                  disabled={!isDirty || saveFile.isPending}
                  title="Discard unsaved changes"
                >
                  <X className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={!isDirty || saveFile.isPending}
                  title="Save (Ctrl+S)"
                >
                  {saveFile.isPending ? (
                    <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4 mr-1" />
                  )}
                  Save
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {selectedFile ? (
            fileLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            ) : (
              <div className="h-[450px] border rounded overflow-hidden">
                <Editor
                  height="100%"
                  path={selectedFile}
                  language={editorLanguage}
                  value={draft}
                  onChange={(value) => setDraft(value ?? '')}
                  theme="vs-dark"
                  options={{
                    readOnly: !isEditable,
                    minimap: { enabled: false },
                    fontSize: 12,
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    automaticLayout: true,
                    tabSize: 2,
                  }}
                  onMount={(editor, monaco) => {
                    // Bind Ctrl+S / Cmd+S to the Save handler so users can
                    // save without leaving the keyboard.
                    editor.addCommand(
                      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
                      () => {
                        handleSave()
                      },
                    )
                  }}
                />
              </div>
            )
          ) : (
            <div className="h-[450px] flex items-center justify-center text-muted-foreground">
              <p className="text-sm">Click a file to view its contents</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete confirmation */}
      <AlertDialog
        open={!!pendingDelete}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete dbt model?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete{' '}
              <span className="font-mono">{pendingDelete?.path}</span> from the
              tenant's dbt project. If a paired schema YAML
              (<span className="font-mono">_{pendingDelete?.name?.replace(/\.sql$/, '')}.yml</span>)
              exists, it will also be removed. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteFile.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteFile.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteFile.isPending ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default ProjectViewer
