/**
 * Tenant Management Page
 * 
 * Portal admin page for managing all tenants (organizations).
 * Supports CRUD, activation, suspension, and filtering.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
  portalAdminService,
  type PortalTenant,
  type PaginatedResponse,
} from '@/services/portalAdminService'
import {
  Search,
  Plus,
  Building2,
  MoreVertical,
  Edit,
  Pause,
  Play,
  Trash2,
  Loader2,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Users,
  ExternalLink,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  suspended: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  pending: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  archived: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
}

const planColors: Record<string, string> = {
  basic: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  professional: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  enterprise: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
}

export const TenantManagementPage: React.FC = () => {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [data, setData] = useState<PaginatedResponse<PortalTenant> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const perPage = 15

  // Dialog states
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingTenant, setEditingTenant] = useState<PortalTenant | null>(null)
  const [suspendingTenant, setSuspendingTenant] = useState<PortalTenant | null>(null)
  const [deletingTenant, setDeletingTenant] = useState<PortalTenant | null>(null)

  const loadTenants = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await portalAdminService.listTenants({
        page,
        per_page: perPage,
        search: search || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      })
      setData(result)
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to load tenants',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }, [page, search, statusFilter, toast])

  useEffect(() => {
    loadTenants()
  }, [loadTenants])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const handleActivate = async (tenant: PortalTenant) => {
    try {
      await portalAdminService.activateTenant(tenant.id)
      toast({ title: 'Success', description: `${tenant.name} activated` })
      loadTenants()
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to activate tenant',
        variant: 'destructive',
      })
    }
  }

  const handleSuspend = async (reason: string) => {
    if (!suspendingTenant) return
    try {
      await portalAdminService.suspendTenant(suspendingTenant.id, reason)
      toast({ title: 'Success', description: `${suspendingTenant.name} suspended` })
      setSuspendingTenant(null)
      loadTenants()
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to suspend tenant',
        variant: 'destructive',
      })
    }
  }

  const handleDelete = async () => {
    if (!deletingTenant) return
    try {
      await portalAdminService.deactivateTenant(deletingTenant.id)
      toast({ title: 'Success', description: `${deletingTenant.name} archived` })
      setDeletingTenant(null)
      loadTenants()
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to archive tenant',
        variant: 'destructive',
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tenant Management</h1>
          <p className="text-muted-foreground">
            Create, configure, and manage platform organizations.
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Tenant
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search tenants..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="icon" onClick={loadTenants}>
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tenant List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Tenants
            {data && (
              <Badge variant="secondary" className="ml-2">
                {data.total}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            All registered organizations on the platform
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : !data?.items?.length ? (
            <div className="text-center py-12">
              <Building2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No tenants found</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-3 font-medium">Organization</th>
                      <th className="text-left p-3 font-medium">Slug</th>
                      <th className="text-left p-3 font-medium">Plan</th>
                      <th className="text-left p-3 font-medium">Status</th>
                      <th className="text-left p-3 font-medium">Created</th>
                      <th className="text-right p-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((tenant) => (
                      <tr key={tenant.id} className="border-b last:border-b-0 hover:bg-muted/30 transition-colors">
                        <td className="p-3">
                          <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-sm">
                              {tenant.name.charAt(0).toUpperCase()}
                            </div>
                            <button 
                              className="font-medium hover:text-primary hover:underline text-left"
                              onClick={() => navigate(`/app/portal/tenants/${tenant.id}`)}
                            >
                              {tenant.name}
                            </button>
                          </div>
                        </td>
                        <td className="p-3">
                          <code className="text-xs bg-muted px-2 py-1 rounded">{tenant.slug}</code>
                        </td>
                        <td className="p-3">
                          <Badge variant="outline" className={planColors[tenant.plan] || planColors.basic}>
                            {tenant.plan}
                          </Badge>
                        </td>
                        <td className="p-3">
                          <Badge variant="outline" className={statusColors[tenant.status] || statusColors.pending}>
                            {tenant.status}
                          </Badge>
                        </td>
                        <td className="p-3 text-muted-foreground">
                          {new Date(tenant.created_at).toLocaleDateString()}
                        </td>
                        <td className="p-3 text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => navigate(`/app/portal/tenants/${tenant.id}`)}>
                                <ExternalLink className="h-4 w-4 mr-2" />
                                View Details
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => navigate(`/app/portal/tenants/${tenant.id}?tab=users`)}>
                                <Users className="h-4 w-4 mr-2" />
                                Manage Users
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={() => setEditingTenant(tenant)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                              {tenant.status === 'active' ? (
                                <DropdownMenuItem onClick={() => setSuspendingTenant(tenant)}>
                                  <Pause className="h-4 w-4 mr-2" />
                                  Suspend
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem onClick={() => handleActivate(tenant)}>
                                  <Play className="h-4 w-4 mr-2" />
                                  Activate
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={() => setDeletingTenant(tenant)}
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Archive
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {data.pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {data.pages} · {data.total} total
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= data.pages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Create Tenant Dialog */}
      <TenantFormDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSave={async (data) => {
          await portalAdminService.createTenant(data)
          toast({ title: 'Success', description: 'Tenant created successfully' })
          setShowCreateDialog(false)
          loadTenants()
        }}
      />

      {/* Edit Tenant Dialog */}
      {editingTenant && (
        <TenantFormDialog
          open={true}
          tenant={editingTenant}
          onClose={() => setEditingTenant(null)}
          onSave={async (data) => {
            await portalAdminService.updateTenant(editingTenant.id, data)
            toast({ title: 'Success', description: 'Tenant updated successfully' })
            setEditingTenant(null)
            loadTenants()
          }}
        />
      )}

      {/* Suspend Dialog */}
      <SuspendTenantDialog
        tenant={suspendingTenant}
        onClose={() => setSuspendingTenant(null)}
        onConfirm={handleSuspend}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={!!deletingTenant} onOpenChange={() => setDeletingTenant(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Archive Tenant</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to archive <strong>{deletingTenant?.name}</strong>?
              This will disable access for all users in this organization. Data will be preserved.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Archive Tenant
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// ---- Tenant Form Dialog ----

interface TenantFormDialogProps {
  open: boolean
  tenant?: PortalTenant
  onClose: () => void
  onSave: (data: Record<string, unknown>) => Promise<void>
}

const TenantFormDialog: React.FC<TenantFormDialogProps> = ({ open, tenant, onClose, onSave }) => {
  const [name, setName] = useState(tenant?.name || '')
  const [slug, setSlug] = useState(tenant?.slug || '')
  const [plan, setPlan] = useState(tenant?.plan || 'basic')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    if (open) {
      setName(tenant?.name || '')
      setSlug(tenant?.slug || '')
      setPlan(tenant?.plan || 'basic')
      setError(null)
    }
  }, [open, tenant])

  // Auto-generate slug from name (only for new tenants)
  useEffect(() => {
    if (!tenant) {
      // Generate slug: lowercase, replace non-alphanumeric with hyphens, ensure starts with letter
      let generatedSlug = name.toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')  // Replace non-alphanumeric with hyphens
        .replace(/^-+|-+$/g, '')       // Trim leading/trailing hyphens
        .replace(/^[^a-z]+/, '')       // Remove leading non-letters (numbers, etc.)
      // If slug is empty or doesn't start with a letter, prefix with 'org-'
      if (!generatedSlug || !/^[a-z]/.test(generatedSlug)) {
        generatedSlug = 'org-' + (generatedSlug || 'new')
      }
      setSlug(generatedSlug)
    }
  }, [name, tenant])

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    if (!slug.trim()) {
      setError('Slug is required')
      return
    }
    // Validate slug format
    if (!/^[a-z][a-z0-9_-]*$/.test(slug.trim())) {
      setError('Slug must start with a letter and contain only lowercase letters, numbers, hyphens, and underscores')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      await onSave({
        name: name.trim(),
        slug: slug.trim(),
        plan,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save tenant'
      setError(msg)
      toast({ title: 'Error', description: msg, variant: 'destructive' })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{tenant ? 'Edit Tenant' : 'Create New Tenant'}</DialogTitle>
          <DialogDescription>
            {tenant ? 'Update organization settings.' : 'Add a new organization to the platform.'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Organization Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Corporation"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="slug">Slug</Label>
            <Input
              id="slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="acme-corp"
              disabled={!!tenant}
            />
            <p className="text-xs text-muted-foreground">
              URL-friendly identifier. {tenant ? 'Cannot be changed.' : 'Auto-generated from name.'}
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="plan">Subscription Plan</Label>
            <Select value={plan} onValueChange={setPlan}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="basic">Basic</SelectItem>
                <SelectItem value="professional">Professional</SelectItem>
                <SelectItem value="enterprise">Enterprise</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isSaving}>
            {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {tenant ? 'Update' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ---- Suspend Tenant Dialog ----

interface SuspendTenantDialogProps {
  tenant: PortalTenant | null
  onClose: () => void
  onConfirm: (reason: string) => Promise<void>
}

const SuspendTenantDialog: React.FC<SuspendTenantDialogProps> = ({ tenant, onClose, onConfirm }) => {
  const [reason, setReason] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (tenant) setReason('')
  }, [tenant])

  const handleConfirm = async () => {
    setIsSaving(true)
    try {
      await onConfirm(reason)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={!!tenant} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Suspend Tenant</DialogTitle>
          <DialogDescription>
            Suspend <strong>{tenant?.name}</strong>? All users will lose access.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="reason">Reason (optional)</Label>
            <Input
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Payment overdue, policy violation, etc."
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="destructive" onClick={handleConfirm} disabled={isSaving}>
            {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Suspend
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
