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
  Key,
  FileText,
  Code2,
  Users,
  Server,
  Building2,
  Upload,
  CalendarClock,
  PieChart,
  LayoutDashboard,
  Sparkles,
  Workflow,
  Zap,
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
  { name: 'Orchestration', href: '/app/orchestration', icon: Workflow },
  { name: 'Extract & Load', href: '/app/pyspark', icon: Upload },
  { name: 'Spark Jobs', href: '/app/jobs', icon: Zap },
  { name: 'Task Scheduler', href: '/app/dags', icon: CalendarClock },
  { name: 'dbt Studio', href: '/app/dbt-studio', icon: GitBranch },
  { name: 'SQL Editor', href: '/app/sql', icon: Code2 },
  { name: 'Charts', href: '/app/charts', icon: PieChart },
  { name: 'Dashboards', href: '/app/dashboards', icon: LayoutDashboard },
]

// AI-powered navigation (special highlight)
const aiNavigation = {
  name: 'Ask AI',
  href: '/app/query',
  icon: Sparkles,
  description: 'Natural language to SQL',
}

// Administration section
const adminNavigation = [
  { name: 'Documentation', href: '/app/docs', icon: Book },
  { name: 'Settings', href: '/app/settings', icon: Settings },
]

// Portal Management (Super Admin only)
const portalNavigation = [
  { name: 'Infrastructure', href: '/app/portal/infrastructure', icon: Server },
  { name: 'Tenant Management', href: '/app/portal/tenants', icon: Building2 },
  { name: 'Roles & Permissions', href: '/app/admin/roles', icon: Key },
  { name: 'Audit Logs', href: '/app/admin/audit', icon: FileText },
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
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
            N
          </div>
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
            {!collapsed && (
              <p className="px-3 mb-2 text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                Portal Management
              </p>
            )}
            {portalNavigation.map((item) => renderNavItem(item))}
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
