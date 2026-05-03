import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  Home,
  Database,
  GitBranch,
  Settings,
  ChevronLeft,
  ChevronRight,
  Book,
  Code2,
  Users,
  Shield,
  Upload,
  PieChart,
  LayoutDashboard,
  Sparkles,
  Calendar,
  Layers,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

// Main navigation - visible to all users
const mainNavigation = [
  { name: 'Data Sources', href: '/app/datasources', icon: Database },
]

// Orchestrate your Data section
const orchestrateNavigation = [
  { name: 'Extract & Load', href: '/app/pipelines', icon: Upload },
  { name: 'Scheduling', href: '/app/jobs', icon: Calendar },
  { name: 'Transform', href: '/app/dbt-studio', icon: GitBranch },
  { name: 'SQL Editor', href: '/app/sql', icon: Code2 },
  { name: 'Datasets', href: '/app/datasets', icon: Layers },
  { name: 'Charts', href: '/app/charts', icon: PieChart },
  { name: 'Dashboards', href: '/app/dashboards', icon: LayoutDashboard },
]

// AI-powered navigation (special highlight)
const aiNavigation = {
  name: 'Ask AI',
  href: '/app/query',
  icon: Sparkles,
  description: 'Natural Language to Insights',
}

// Administration section
const adminNavigation = [
  { name: 'Documentation', href: '/app/docs', icon: Book },
  { name: 'Settings', href: '/app/settings', icon: Settings },
]



export function Sidebar() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const { user } = useAuth()

  const isSuperAdmin = user?.roles?.includes('super_admin')
  const isTenantAdmin = user?.roles?.includes('tenant_admin')
  const canManageUsers = isSuperAdmin || isTenantAdmin
  
  // Get tenant name for home display
  const tenantName = user?.tenant_name || 'Home'

  const renderNavItem = (item: { name: string; href: string; icon: React.ElementType }, customName?: string) => {
    const isActive = location.pathname === item.href || 
      (item.href !== '/app/dashboard' && location.pathname.startsWith(item.href))
    return (
      <Link
        key={item.name}
        to={item.href}
        className={cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
        )}
      >
        <item.icon className="h-5 w-5 shrink-0" />
        {!collapsed && <span>{customName || item.name}</span>}
      </Link>
    )
  }

  return (
    <div
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b px-4">
        <Link to="/" className="flex items-center gap-2">
          <img
            src="/mobius_strip.png"
            alt="NovaSight"
            className="h-8 w-auto object-contain"
          />
          {!collapsed && (
            <span className="text-lg font-semibold">NovaSight</span>
          )}
        </Link>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-4 space-y-6">
        {/* Tenant Home */}
        <div>
          <Link
            to="/app/dashboard"
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              location.pathname === '/app/dashboard'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
          >
            <Home className="h-5 w-5 shrink-0" />
            {!collapsed && <span>{tenantName} Home</span>}
          </Link>
        </div>

        {/* Manage Connections */}
        <div>
          {!collapsed && (
            <p className="px-3 mb-2 text-xs font-semibold uppercase text-muted-foreground tracking-wider">
              Manage Connections
            </p>
          )}
          {mainNavigation.map((item) => renderNavItem(item))}
        </div>

        {/* Orchestrate your Data */}
        <div>
          {!collapsed && (
            <p className="px-3 mb-2 text-xs font-semibold uppercase text-muted-foreground tracking-wider">
              Orchestrate your Data
            </p>
          )}
          {orchestrateNavigation.map((item) => renderNavItem(item))}
        </div>

        {/* Ask AI - Special Highlight */}
        <div>
          <Link
            to={aiNavigation.href}
            className={cn(
              'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
              location.pathname === aiNavigation.href
                ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/25'
                : 'bg-gradient-to-r from-violet-500/10 to-indigo-500/10 text-violet-700 dark:text-violet-300 hover:from-violet-500/20 hover:to-indigo-500/20 hover:shadow-md hover:shadow-violet-500/10 border border-violet-500/20'
            )}
          >
            <div className={cn(
              'relative',
              location.pathname !== aiNavigation.href && 'animate-pulse'
            )}>
              <aiNavigation.icon className="h-5 w-5 shrink-0" />
              <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-violet-500 animate-ping" />
              <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-violet-400" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-semibold">{aiNavigation.name}</span>
                <span className={cn(
                  'text-xs',
                  location.pathname === aiNavigation.href 
                    ? 'text-violet-200' 
                    : 'text-violet-500 dark:text-violet-400'
                )}>
                  {aiNavigation.description}
                </span>
              </div>
            )}
          </Link>
        </div>

        {/* Administration */}
        <div>
          {!collapsed && (
            <p className="px-3 mb-2 text-xs font-semibold uppercase text-muted-foreground tracking-wider">
              Administration
            </p>
          )}
          {adminNavigation.map((item) => renderNavItem(item))}
        </div>

        {/* User Management (Tenant Admin - non Super Admin) */}
        {isTenantAdmin && !isSuperAdmin && (
          <div>
            {!collapsed && (
              <p className="px-3 mb-2 text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                Organization
              </p>
            )}
            <Link
              to="/app/admin/users"
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                location.pathname.startsWith('/app/admin/users')
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <Users className="h-5 w-5 shrink-0" />
              {!collapsed && <span>User Management</span>}
            </Link>
          </div>
        )}

        {/* Portal Management (Super Admin only) */}
        {isSuperAdmin && (
          <div>
            <Link
              to="/app/portal"
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                location.pathname.startsWith('/app/portal')
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <Shield className="h-5 w-5 shrink-0" />
              {!collapsed && <span>Portal Management</span>}
            </Link>
          </div>
        )}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  )
}
