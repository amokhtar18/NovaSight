/**
 * Portal Management Layout
 * 
 * Shell layout for the super admin portal management area.
 * Provides a collapsible sidebar with portal-specific navigation and a content area.
 */

import React, { useState, useEffect } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import {
  LayoutDashboard,
  Building2,
  Server,
  ArrowLeft,
  Shield,
  ChevronRight,
  ChevronLeft,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const PORTAL_SIDEBAR_COLLAPSED_KEY = 'novasight-portal-sidebar-collapsed'

const portalNav = [
  { 
    name: 'Overview', 
    href: '/app/portal', 
    icon: LayoutDashboard,
    description: 'Dashboard & statistics',
    exact: true,
  },
  { 
    name: 'Tenants', 
    href: '/app/portal/tenants', 
    icon: Building2,
    description: 'Manage organizations & users',
  },
  { 
    name: 'Infrastructure', 
    href: '/app/portal/infrastructure', 
    icon: Server,
    description: 'Server configurations',
  },
]

export const PortalLayout: React.FC = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()

  // Sidebar collapsed state with localStorage persistence
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem(PORTAL_SIDEBAR_COLLAPSED_KEY)
    return saved === 'true'
  })

  // Persist collapsed state to localStorage
  useEffect(() => {
    localStorage.setItem(PORTAL_SIDEBAR_COLLAPSED_KEY, String(collapsed))
  }, [collapsed])

  const isSuperAdmin = user?.roles?.includes('super_admin')

  if (!isSuperAdmin) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <Shield className="h-16 w-16 text-muted-foreground mx-auto" />
          <h2 className="text-2xl font-bold">Access Denied</h2>
          <p className="text-muted-foreground">
            Portal management is restricted to super administrators.
          </p>
          <Button onClick={() => navigate('/app/dashboard')}>
            Return to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-full -m-6">
        {/* Portal Sidebar */}
        <div className={cn(
          'border-r bg-card flex flex-col transition-all duration-300',
          collapsed ? 'w-16' : 'w-72'
        )}>
          {/* Header */}
          <div className="p-4 border-b">
            <div className="flex items-center gap-2 mb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shrink-0">
                <Shield className="h-4 w-4" />
              </div>
              {!collapsed && (
                <div>
                  <h2 className="text-sm font-semibold">Portal Management</h2>
                  <p className="text-xs text-muted-foreground">Super Admin</p>
                </div>
              )}
            </div>
            {collapsed ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="w-full"
                    onClick={() => navigate('/app/dashboard')}
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  Back to Application
                </TooltipContent>
              </Tooltip>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-muted-foreground hover:text-foreground"
                onClick={() => navigate('/app/dashboard')}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Application
              </Button>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1">
            {portalNav.map((item) => {
              const isActive = item.exact
                ? location.pathname === item.href
                : location.pathname.startsWith(item.href)
              
              const linkContent = (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors group',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    collapsed && 'justify-center px-2'
                  )}
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  {!collapsed && (
                    <>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium">{item.name}</div>
                        <div className={cn(
                          'text-xs truncate',
                          isActive ? 'text-primary-foreground/70' : 'text-muted-foreground'
                        )}>
                          {item.description}
                        </div>
                      </div>
                      <ChevronRight className={cn(
                        'h-4 w-4 shrink-0 transition-transform',
                        isActive ? 'text-primary-foreground/70' : 'opacity-0 group-hover:opacity-50'
                      )} />
                    </>
                  )}
                </Link>
              )

              if (collapsed) {
                return (
                  <Tooltip key={item.name}>
                    <TooltipTrigger asChild>
                      {linkContent}
                    </TooltipTrigger>
                    <TooltipContent side="right" className="flex flex-col">
                      <span className="font-medium">{item.name}</span>
                      <span className="text-xs text-muted-foreground">{item.description}</span>
                    </TooltipContent>
                  </Tooltip>
                )
              }

              return linkContent
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t">
            {!collapsed && (
              <div className="text-xs text-muted-foreground mb-3">
                Logged in as <span className="font-medium text-foreground">{user?.email}</span>
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                'w-full',
                collapsed ? 'justify-center' : 'justify-start'
              )}
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? (
                <PanelLeft className="h-4 w-4" />
              ) : (
                <>
                  <PanelLeftClose className="h-4 w-4 mr-2" />
                  Collapse sidebar
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-muted/40">
          <Outlet />
        </div>
      </div>
    </TooltipProvider>
  )
}
