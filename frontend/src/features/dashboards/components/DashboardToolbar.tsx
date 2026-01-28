/**
 * Dashboard Toolbar Component
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Edit3, 
  Eye, 
  Share2, 
  Settings, 
  MoreVertical,
  Trash2,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useDeleteDashboard } from '../hooks/useDashboards'
import type { Dashboard } from '@/types/dashboard'

interface DashboardToolbarProps {
  dashboard: Dashboard
  isEditing: boolean
  onEditToggle: () => void
}

export function DashboardToolbar({ 
  dashboard, 
  isEditing, 
  onEditToggle 
}: DashboardToolbarProps) {
  const navigate = useNavigate()
  const deleteMutation = useDeleteDashboard()
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this dashboard?')) {
      await deleteMutation.mutateAsync(dashboard.id)
      navigate('/dashboards')
    }
  }
  
  const handleRefresh = () => {
    setIsRefreshing(true)
    // Force refetch all widget data
    window.location.reload()
  }
  
  return (
    <div className="flex items-center justify-between px-6 py-4 border-b bg-background">
      <div>
        <h1 className="text-2xl font-bold">{dashboard.name}</h1>
        {dashboard.description && (
          <p className="text-sm text-muted-foreground mt-1">
            {dashboard.description}
          </p>
        )}
      </div>
      
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
        
        <Button
          variant={isEditing ? 'default' : 'outline'}
          size="sm"
          onClick={onEditToggle}
        >
          {isEditing ? (
            <>
              <Eye className="h-4 w-4 mr-2" />
              View Mode
            </>
          ) : (
            <>
              <Edit3 className="h-4 w-4 mr-2" />
              Edit
            </>
          )}
        </Button>
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={handleDelete}
              className="text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
