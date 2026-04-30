/**
 * AI Workbench — "Agent" tab
 *
 * Lets a tenant admin configure the NovaSight Ollama agent: default
 * model, system prompt, enabled MCP / tool flags, and sampling
 * parameters. Backed by `/api/v1/ai/agent/config`.
 */

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Loader2, Save } from 'lucide-react'
import {
  agentService,
  type AgentConfig,
  type AgentConfigUpdate,
} from '@/services/agentService'

const KNOWN_TOOLS = ['superset-mcp', 'dbt-mcp', 'sql-runner']

export function AgentConfigTab() {
  const [config, setConfig] = useState<AgentConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    agentService
      .getConfig()
      .then((c) => {
        if (mounted) setConfig(c)
      })
      .catch((e) => {
        if (mounted) setError(e?.message || 'Failed to load agent config')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const onSave = async () => {
    if (!config) return
    setSaving(true)
    setError(null)
    try {
      const updates: AgentConfigUpdate = {
        default_model: config.default_model,
        system_prompt: config.system_prompt,
        enabled_tools: config.enabled_tools,
        sampling: config.sampling,
      }
      const next = await agentService.updateConfig(updates)
      setConfig(next)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Save failed'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!config) {
    return (
      <div className="text-destructive py-8 text-center">
        {error || 'Agent config unavailable'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Model</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="agent-default-model">Default Ollama model</Label>
            <Input
              id="agent-default-model"
              value={config.default_model || ''}
              onChange={(e) =>
                setConfig({ ...config, default_model: e.target.value || null })
              }
              placeholder="e.g. llama3.1:8b"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>System prompt</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={config.system_prompt || ''}
            onChange={(e) =>
              setConfig({ ...config, system_prompt: e.target.value })
            }
            rows={8}
            placeholder="System prompt for the agent…"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Tools</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {KNOWN_TOOLS.map((tool) => {
            const enabled = !!config.enabled_tools?.[tool]
            return (
              <div
                key={tool}
                className="flex items-center justify-between rounded border p-3"
              >
                <div>
                  <div className="font-medium">{tool}</div>
                  <div className="text-xs text-muted-foreground">
                    {tool === 'superset-mcp'
                      ? 'Read / build charts and dashboards through Superset'
                      : tool === 'dbt-mcp'
                        ? 'Inspect and run dbt models'
                        : 'Execute SQL against the tenant ClickHouse DB'}
                  </div>
                </div>
                <Switch
                  checked={enabled}
                  onCheckedChange={(checked) =>
                    setConfig({
                      ...config,
                      enabled_tools: {
                        ...(config.enabled_tools || {}),
                        [tool]: checked,
                      },
                    })
                  }
                />
              </div>
            )
          })}
        </CardContent>
      </Card>

      {error && <div className="text-destructive text-sm">{error}</div>}

      <div className="flex justify-end">
        <Button onClick={onSave} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>
    </div>
  )
}

export default AgentConfigTab
