/**
 * Dashboards List Page
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, LayoutDashboard, Calendar, User } from 'lucide-react'
import { useDashboards, useCreateDashboard } from '../hooks/useDashboards'
import type { Dashboard } from '@/types/dashboard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'

export function DashboardsListPage() {
  const navigate = useNavigate()
  const { data: dashboards, isLoading } = useDashboards()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboards</h1>
          <p className="text-muted-foreground mt-1">
            Create and manage your analytics dashboards
          </p>
        </div>
        
        <CreateDashboardDialog 
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
        />
      </div>
      
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : dashboards && dashboards.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dashboards.map((dashboard: Dashboard) => (
            <Card 
              key={dashboard.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => navigate(`/dashboards/${dashboard.id}`)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <LayoutDashboard className="h-8 w-8 text-primary" />
                  <div className="text-xs text-muted-foreground">
                    {dashboard.widgets.length} widgets
                  </div>
                </div>
                <CardTitle className="mt-2">{dashboard.name}</CardTitle>
                <CardDescription>
                  {dashboard.description || 'No description'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {new Date(dashboard.updated_at).toLocaleDateString()}
                  </div>
                  <div className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {dashboard.created_by}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center">
          <LayoutDashboard className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No dashboards yet</h3>
          <p className="text-muted-foreground mb-4">
            Create your first dashboard to get started
          </p>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Dashboard
          </Button>
        </Card>
      )}
    </div>
  )
}

interface CreateDashboardDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function CreateDashboardDialog({ open, onOpenChange }: CreateDashboardDialogProps) {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const createMutation = useCreateDashboard()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const dashboard = await createMutation.mutateAsync({
      name,
      description,
      auto_refresh: false,
      refresh_interval: 30,
      is_public: false,
    })
    
    onOpenChange(false)
    setName('')
    setDescription('')
    navigate(`/dashboards/${dashboard.id}`)
  }
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Dashboard
        </Button>
      </DialogTrigger>
      
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Dashboard</DialogTitle>
          <DialogDescription>
            Create a new dashboard to visualize your data
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Dashboard Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Sales Overview"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this dashboard show?"
              rows={3}
            />
          </div>
          
          <div className="flex justify-end gap-2">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
