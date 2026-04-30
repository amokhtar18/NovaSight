/**
 * AI Workbench — "MCP Servers" tab
 *
 * Register / remove MCP servers, ping their /health endpoint, and
 * refresh the list of advertised tools. Backed by
 * `/api/v1/ai/mcp/*`.
 */

import { useEffect, useState } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Loader2, Plus, RefreshCw, Trash2, Activity } from 'lucide-react'
import { mcpService, type MCPServer } from '@/services/mcpService'

export function MCPServersTab() {
  const [servers, setServers] = useState<MCPServer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [healthMap, setHealthMap] = useState<Record<string, boolean>>({})

  // New server form state
  const [newName, setNewName] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [newAuth, setNewAuth] = useState('')
  const [creating, setCreating] = useState(false)

  const reload = async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await mcpService.listServers()
      setServers(list)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load MCP servers')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
  }, [])

  const onAdd = async () => {
    if (!newName.trim() || !newUrl.trim()) return
    setCreating(true)
    setError(null)
    try {
      await mcpService.registerServer({
        name: newName.trim(),
        base_url: newUrl.trim(),
        auth_header: newAuth.trim() || undefined,
        enabled: true,
      })
      setNewName('')
      setNewUrl('')
      setNewAuth('')
      await reload()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Could not register server')
    } finally {
      setCreating(false)
    }
  }

  const onCheckHealth = async (name: string) => {
    try {
      const result = await mcpService.health(name)
      setHealthMap((h) => ({ ...h, [name]: result.healthy }))
    } catch {
      setHealthMap((h) => ({ ...h, [name]: false }))
    }
  }

  const onRefresh = async (name: string) => {
    try {
      await mcpService.refreshTools(name)
      await reload()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Refresh failed')
    }
  }

  const onDelete = async (name: string) => {
    try {
      await mcpService.deleteServer(name)
      await reload()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Register a new MCP server</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <Label htmlFor="mcp-name">Name</Label>
              <Input
                id="mcp-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="superset-mcp"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mcp-url">URL</Label>
              <Input
                id="mcp-url"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="http://superset-mcp:8080"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mcp-auth">Auth header (optional)</Label>
              <Input
                id="mcp-auth"
                value={newAuth}
                onChange={(e) => setNewAuth(e.target.value)}
                placeholder="Bearer …"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={onAdd} disabled={creating}>
              {creating ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Register
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Registered servers</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : servers.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No MCP servers registered yet.
            </div>
          ) : (
            <ul className="divide-y">
              {servers.map((s) => {
                const health = healthMap[s.name]
                return (
                  <li
                    key={s.id}
                    className="flex items-center justify-between gap-4 py-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{s.name}</span>
                        {health === undefined ? null : (
                          <Badge
                            variant={health ? 'default' : 'destructive'}
                            className="gap-1"
                          >
                            <Activity className="h-3 w-3" />
                            {health ? 'healthy' : 'unhealthy'}
                          </Badge>
                        )}
                      </div>
                      <div className="truncate text-xs text-muted-foreground">
                        {s.base_url}
                      </div>
                      {s.tools_snapshot.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {s.tools_snapshot.map((t) => (
                            <Badge key={t} variant="outline" className="text-xs">
                              {t}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Check health"
                        onClick={() => onCheckHealth(s.name)}
                      >
                        <Activity className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Refresh tools"
                        onClick={() => onRefresh(s.name)}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Remove"
                        onClick={() => onDelete(s.name)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      {error && <div className="text-destructive text-sm">{error}</div>}
    </div>
  )
}

export default MCPServersTab
