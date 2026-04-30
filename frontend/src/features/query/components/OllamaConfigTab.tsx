/**
 * AI Workbench — "Ollama" tab
 *
 * Read / update the per-tenant default Ollama model and embedding
 * model, and trigger a model pull on the running Ollama daemon.
 * Backed by `/api/v1/ai/ollama/*`.
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
import { Loader2, Save, Download } from 'lucide-react'
import {
  ollamaService,
  type OllamaConfig,
} from '@/services/ollamaService'

export function OllamaConfigTab() {
  const [config, setConfig] = useState<OllamaConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pulling, setPulling] = useState(false)
  const [pullModel, setPullModel] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    ollamaService
      .getConfig()
      .then((c) => {
        if (mounted) setConfig(c)
      })
      .catch((e) => {
        if (mounted) setError(e?.message || 'Failed to load Ollama config')
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
    setInfo(null)
    try {
      const next = await ollamaService.updateConfig({
        default_model: config.default_model,
        embedding_model: config.embedding_model,
      })
      setConfig(next)
      setInfo('Saved')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const onPull = async () => {
    if (!pullModel.trim()) return
    setPulling(true)
    setError(null)
    setInfo(null)
    try {
      await ollamaService.pullModel(pullModel.trim())
      setInfo(`Pulled ${pullModel}`)
      setPullModel('')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Pull failed')
    } finally {
      setPulling(false)
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
        {error || 'Ollama config unavailable'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Runtime</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <Label>Base URL</Label>
            <Input value={config.base_url} disabled />
            <p className="text-xs text-muted-foreground">
              Configured via the platform-level{' '}
              <code>OLLAMA_BASE_URL</code> environment variable.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Default models</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="ollama-default">Default chat model</Label>
            <Input
              id="ollama-default"
              value={config.default_model || ''}
              onChange={(e) =>
                setConfig({ ...config, default_model: e.target.value || null })
              }
              placeholder="e.g. llama3.1:8b"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ollama-embed">Embedding model</Label>
            <Input
              id="ollama-embed"
              value={config.embedding_model || ''}
              onChange={(e) =>
                setConfig({
                  ...config,
                  embedding_model: e.target.value || null,
                })
              }
              placeholder="e.g. nomic-embed-text"
            />
          </div>
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pull a new model</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              value={pullModel}
              onChange={(e) => setPullModel(e.target.value)}
              placeholder="e.g. llama3.1:8b"
            />
            <Button onClick={onPull} disabled={pulling || !pullModel.trim()}>
              {pulling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Pull
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Triggers <code>POST /api/pull</code> on the configured Ollama
            daemon. Large models can take several minutes.
          </p>
        </CardContent>
      </Card>

      {error && <div className="text-destructive text-sm">{error}</div>}
      {info && <div className="text-sm text-emerald-600">{info}</div>}
    </div>
  )
}

export default OllamaConfigTab
