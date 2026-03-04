/**
 * Infrastructure Configuration Page
 *
 * Admin page for configuring infrastructure server connections
 * (ClickHouse, Spark, Ollama) — uses shadcn/ui design system.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  Cpu,
  BrainCircuit,
  RefreshCw,
  Zap,
  Settings2,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Server,
  Shield,
  Info,
  Circle,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { infrastructureService } from '../../services/infrastructureService';
import type {
  InfrastructureConfig,
  InfrastructureServiceType,
  InfrastructureConfigCreate,
  InfrastructureConfigTestResult,
} from '../../types/infrastructure';

// ─── Service Metadata ──────────────────────────────────────────────────────────

interface ServiceMeta {
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;        // accent ring/badge color class
  iconBg: string;       // icon wrapper bg
  iconColor: string;    // lucide icon fill
  gradient: string;     // top-bar gradient
}

const SERVICE_META: Record<InfrastructureServiceType, ServiceMeta> = {
  clickhouse: {
    label: 'ClickHouse',
    description: 'Column-oriented OLAP database for analytics',
    icon: Database,
    color: 'text-amber-600',
    iconBg: 'bg-amber-100 dark:bg-amber-950/40',
    iconColor: 'text-amber-600 dark:text-amber-400',
    gradient: 'from-amber-500 to-orange-500',
  },
  spark: {
    label: 'Apache Spark',
    description: 'Distributed computing for big data processing',
    icon: Cpu,
    color: 'text-orange-600',
    iconBg: 'bg-orange-100 dark:bg-orange-950/40',
    iconColor: 'text-orange-600 dark:text-orange-400',
    gradient: 'from-orange-500 to-red-500',
  },
  ollama: {
    label: 'Ollama LLM',
    description: 'Local AI server for natural language queries',
    icon: BrainCircuit,
    color: 'text-violet-600',
    iconBg: 'bg-violet-100 dark:bg-violet-950/40',
    iconColor: 'text-violet-600 dark:text-violet-400',
    gradient: 'from-violet-500 to-purple-500',
  },
};

const SERVICE_TYPES: InfrastructureServiceType[] = ['clickhouse', 'spark', 'ollama'];

// ─── Status Badge ───────────────────────────────────────────────────────────────

type ConnectionStatus = 'connected' | 'disconnected' | 'testing' | 'unknown';

const StatusIndicator: React.FC<{ status: ConnectionStatus }> = ({ status }) => {
  const config: Record<ConnectionStatus, { variant: 'success' | 'destructive' | 'warning' | 'outline'; label: string; dot: string }> = {
    connected:    { variant: 'success',     label: 'Connected',    dot: 'bg-green-500'  },
    disconnected: { variant: 'destructive', label: 'Disconnected', dot: 'bg-red-500'    },
    testing:      { variant: 'warning',     label: 'Testing…',     dot: 'bg-yellow-500' },
    unknown:      { variant: 'outline',     label: 'Not Tested',   dot: 'bg-gray-400'   },
  };
  const c = config[status];
  return (
    <Badge variant={c.variant} className="gap-1.5 font-medium">
      {status === 'testing' ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        <Circle className={`h-2 w-2 fill-current ${c.dot}`} />
      )}
      {c.label}
    </Badge>
  );
};

// ─── Service Card ───────────────────────────────────────────────────────────────

interface ServiceCardProps {
  serviceType: InfrastructureServiceType;
  config: InfrastructureConfig | null;
  source: 'database' | 'environment';
  testResult: InfrastructureConfigTestResult | null;
  isTesting: boolean;
  onEdit: () => void;
  onTest: () => void;
}

const ServiceCard: React.FC<ServiceCardProps> = ({
  serviceType,
  config,
  source,
  testResult,
  isTesting,
  onEdit,
  onTest,
}) => {
  const meta = SERVICE_META[serviceType];
  const Icon = meta.icon;

  const getStatus = (): ConnectionStatus => {
    if (isTesting) return 'testing';
    if (testResult === null) return 'unknown';
    return testResult.success ? 'connected' : 'disconnected';
  };

  const status = getStatus();

  return (
    <Card className="group relative overflow-hidden transition-all duration-200 hover:shadow-md">
      {/* Colored top accent bar */}
      <div className={`h-1 bg-gradient-to-r ${meta.gradient}`} />

      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${meta.iconBg}`}>
              <Icon className={`h-5 w-5 ${meta.iconColor}`} />
            </div>
            <div>
              <CardTitle className="text-base">{meta.label}</CardTitle>
              <CardDescription className="text-xs mt-0.5">{meta.description}</CardDescription>
            </div>
          </div>
          <StatusIndicator status={status} />
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pb-3">
        {/* Connection details */}
        <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Server className="h-3.5 w-3.5" />
              Host
            </span>
            <span className="font-mono text-xs font-medium">{config?.host || 'localhost'}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Shield className="h-3.5 w-3.5" />
              Port
            </span>
            <span className="font-mono text-xs font-medium">{config?.port || infrastructureService.getDefaultPort(serviceType)}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Info className="h-3.5 w-3.5" />
              Source
            </span>
            <Badge variant={source === 'database' ? 'info' : 'secondary'} className="text-[10px] px-1.5 py-0">
              {source === 'database' ? 'Custom' : 'Default'}
            </Badge>
          </div>
        </div>

        {/* Test result details */}
        {testResult && (
          <div className={`rounded-lg border p-3 text-sm ${
            testResult.success
              ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/30'
              : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30'
          }`}>
            {testResult.success ? (
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-green-700 dark:text-green-300">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Connection successful
                </div>
                <div className="flex items-center gap-3 text-xs text-green-600 dark:text-green-400">
                  {testResult.latency_ms != null && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {testResult.latency_ms.toFixed(0)} ms
                    </span>
                  )}
                  {testResult.server_version && (
                    <span>v{testResult.server_version}</span>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-red-700 dark:text-red-300">
                  <XCircle className="h-3.5 w-3.5" />
                  Connection failed
                </div>
                <p className="text-xs text-red-600 dark:text-red-400 line-clamp-2">
                  {testResult.message}
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>

      <CardFooter className="gap-2 pt-0">
        <Button
          variant="outline"
          size="sm"
          className="flex-1"
          disabled={isTesting}
          onClick={onTest}
        >
          {isTesting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Zap className="h-3.5 w-3.5" />
          )}
          {isTesting ? 'Testing…' : 'Test'}
        </Button>
        <Button
          size="sm"
          className="flex-1"
          onClick={onEdit}
        >
          <Settings2 className="h-3.5 w-3.5" />
          Configure
        </Button>
      </CardFooter>
    </Card>
  );
};

// ─── Configuration Dialog ───────────────────────────────────────────────────────

interface ConfigDialogProps {
  open: boolean;
  serviceType: InfrastructureServiceType;
  existingConfig: InfrastructureConfig | null;
  onSave: (config: InfrastructureConfigCreate) => Promise<void>;
  onClose: () => void;
  onTest: (config: Partial<InfrastructureConfigCreate>) => Promise<InfrastructureConfigTestResult>;
}

const ConfigDialog: React.FC<ConfigDialogProps> = ({
  open,
  serviceType,
  existingConfig,
  onSave,
  onClose,
  onTest,
}) => {
  const meta = SERVICE_META[serviceType];
  const Icon = meta.icon;
  const defaultSettings = infrastructureService.getDefaultSettings(serviceType);

  // Strip host/port from settings — the backend env fallback injects them
  // into settings, but they belong at the top level of the config.
  const cleanSettings = (raw: Record<string, unknown> | undefined) => {
    if (!raw) return {};
    const { host, port, ...rest } = raw as Record<string, unknown> & { host?: unknown; port?: unknown };
    return rest;
  };

  const [formData, setFormData] = useState({
    name: existingConfig?.name || `${meta.label} Connection`,
    description: existingConfig?.description || '',
    host: existingConfig?.host || 'localhost',
    port: existingConfig?.port || infrastructureService.getDefaultPort(serviceType),
    settings: { ...defaultSettings, ...cleanSettings(existingConfig?.settings) } as Record<string, unknown>,
    is_active: existingConfig?.is_active ?? true,
  });

  const [testResult, setTestResult] = useState<InfrastructureConfigTestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when dialog opens with new service
  useEffect(() => {
    if (open) {
      setFormData({
        name: existingConfig?.name || `${meta.label} Connection`,
        description: existingConfig?.description || '',
        host: existingConfig?.host || 'localhost',
        port: existingConfig?.port || infrastructureService.getDefaultPort(serviceType),
        settings: { ...defaultSettings, ...cleanSettings(existingConfig?.settings) } as Record<string, unknown>,
        is_active: existingConfig?.is_active ?? true,
      });
      setTestResult(null);
      setError(null);
    }
  }, [open, serviceType]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => {
      const updated = {
        ...prev,
        [name]: type === 'number' ? parseInt(value, 10) || 0 : value,
      };
      // Auto-fill Spark master_url when host or port changes
      if (serviceType === 'spark' && (name === 'host' || name === 'port')) {
        const host = name === 'host' ? value : prev.host;
        const port = name === 'port' ? (parseInt(value, 10) || 0) : prev.port;
        if (host && port) {
          updated.settings = { ...updated.settings, master_url: `spark://${host}:${port}` };
        }
      }
      return updated;
    });
  };

  const updateSetting = (key: string, value: unknown) => {
    setFormData(prev => ({ ...prev, settings: { ...prev.settings, [key]: value } }));
  };

  const handleTest = async () => {
    setIsTesting(true);
    setError(null);
    try {
      const result = await onTest({
        service_type: serviceType,
        host: formData.host,
        port: formData.port,
        settings: formData.settings,
      });
      setTestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test failed');
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      await onSave({
        service_type: serviceType,
        name: formData.name,
        description: formData.description,
        host: formData.host,
        port: formData.port,
        settings: formData.settings,
        is_active: formData.is_active,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
      setIsSaving(false);
    }
  };

  // ── Field helper ──────────────────────────────────────────────────────────
  const field = (label: string, name: string, opts?: {
    type?: string; placeholder?: string; hint?: string;
    min?: number; max?: number; step?: number;
  }) => {
    const val = formData.settings[name];
    return (
      <div className="space-y-1.5">
        <Label htmlFor={`s-${name}`}>{label}</Label>
        <Input
          id={`s-${name}`}
          type={opts?.type || 'text'}
          value={val as string | number ?? ''}
          placeholder={opts?.placeholder}
          min={opts?.min}
          max={opts?.max}
          step={opts?.step}
          onChange={(e) => {
            const v = opts?.type === 'number'
              ? (opts?.step && opts.step < 1 ? parseFloat(e.target.value) : parseInt(e.target.value, 10))
              : e.target.value;
            updateSetting(name, v);
          }}
        />
        {opts?.hint && <p className="text-[11px] text-muted-foreground">{opts.hint}</p>}
      </div>
    );
  };

  // ── Per-service settings ──────────────────────────────────────────────────
  const renderSettings = () => {
    switch (serviceType) {
      case 'clickhouse':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {field('Database', 'database', { placeholder: 'novasight' })}
              {field('User', 'user', { placeholder: 'default' })}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="s-password">Password</Label>
              <Input
                id="s-password"
                type="password"
                value={formData.settings.password as string || ''}
                placeholder="Leave empty to keep existing"
                onChange={(e) => updateSetting('password', e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Switch
                id="s-secure"
                checked={formData.settings.secure as boolean || false}
                onCheckedChange={(v) => updateSetting('secure', v)}
              />
              <Label htmlFor="s-secure" className="cursor-pointer">Use TLS/SSL encryption</Label>
            </div>
          </div>
        );

      case 'spark':
        return (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="s-master_url">Master URL</Label>
              <Input
                id="s-master_url"
                value={formData.settings.master_url as string ?? ''}
                placeholder="spark://spark-master:7077"
                readOnly
                className="bg-muted/50 cursor-not-allowed"
              />
              <p className="text-[11px] text-muted-foreground">Auto-generated from Host and Port above</p>
            </div>
            {field('SSH Host', 'ssh_host', { placeholder: 'spark-server', hint: 'Hostname for SSH-based remote execution (optional)' })}
            <div className="grid grid-cols-2 gap-4">
              {field('SSH User', 'ssh_user', { placeholder: 'spark' })}
              {field('Web UI Port', 'webui_port', { type: 'number', min: 1, hint: 'Spark Master Web UI port for testing connectivity' })}
            </div>
          </div>
        );

      case 'ollama':
        return (
          <div className="space-y-4">
            {field('Base URL', 'base_url', { placeholder: 'http://ollama:11434' })}
            <div className="grid grid-cols-2 gap-4">
              {field('Default Model', 'default_model', { placeholder: 'llama3.2', hint: 'Model name available on the Ollama server' })}
              {field('Request Timeout', 'request_timeout', { type: 'number', min: 10, max: 600, hint: 'Seconds' })}
            </div>
            <div className="grid grid-cols-3 gap-4">
              {field('Context Window', 'num_ctx', { type: 'number', min: 512, step: 512, hint: 'Tokens' })}
              {field('Temperature', 'temperature', { type: 'number', min: 0, max: 2, step: 0.1 })}
              {field('Keep Alive', 'keep_alive', { placeholder: '5m', hint: 'e.g. 5m, 1h' })}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${meta.iconBg}`}>
              <Icon className={`h-4.5 w-4.5 ${meta.iconColor}`} />
            </div>
            <div>
              <DialogTitle>Configure {meta.label}</DialogTitle>
              <DialogDescription>Update connection settings for {meta.label}.</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-2">
          {/* ── Basic info ─────────────────────────────────────────── */}
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="cfg-name">Configuration Name</Label>
              <Input id="cfg-name" name="name" value={formData.name} onChange={handleInputChange} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cfg-desc">Description</Label>
              <Textarea id="cfg-desc" name="description" value={formData.description} onChange={handleInputChange} rows={2} className="resize-none" />
            </div>
          </div>

          <Separator />

          {/* ── Connection ─────────────────────────────────────────── */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold flex items-center gap-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              Connection
            </h4>
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2 space-y-1.5">
                <Label htmlFor="cfg-host">Host</Label>
                <Input id="cfg-host" name="host" value={formData.host} onChange={handleInputChange} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cfg-port">Port</Label>
                <Input id="cfg-port" name="port" type="number" value={formData.port} onChange={handleInputChange} />
              </div>
            </div>
          </div>

          <Separator />

          {/* ── Service-specific settings ──────────────────────────── */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              {meta.label} Settings
            </h4>
            {renderSettings()}
          </div>

          {/* ── Test result ────────────────────────────────────────── */}
          {testResult && (
            <div className={`rounded-lg border p-4 ${
              testResult.success
                ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/30'
                : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30'
            }`}>
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-600" />
                )}
                <span className={`text-sm font-medium ${testResult.success ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                  {testResult.success ? 'Connection successful' : 'Connection failed'}
                </span>
                {testResult.latency_ms != null && (
                  <span className="text-xs text-muted-foreground ml-auto">
                    {testResult.latency_ms.toFixed(0)} ms
                  </span>
                )}
              </div>
              {testResult.server_version && (
                <p className="text-xs text-muted-foreground mt-1">Server version: {testResult.server_version}</p>
              )}
              {!testResult.success && testResult.message && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1">{testResult.message}</p>
              )}
            </div>
          )}

          {/* ── Error ──────────────────────────────────────────────── */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30 p-3">
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="outline" onClick={handleTest} disabled={isTesting}>
            {isTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            {isTesting ? 'Testing…' : 'Test Connection'}
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            {isSaving ? 'Saving…' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ─── Loading Skeleton ───────────────────────────────────────────────────────────

const CardSkeleton: React.FC = () => (
  <Card className="overflow-hidden">
    <div className="h-1 bg-muted" />
    <CardHeader className="pb-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-40" />
          </div>
        </div>
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
    </CardHeader>
    <CardContent className="pb-3">
      <Skeleton className="h-24 w-full rounded-lg" />
    </CardContent>
    <CardFooter className="gap-2 pt-0">
      <Skeleton className="h-8 flex-1 rounded-md" />
      <Skeleton className="h-8 flex-1 rounded-md" />
    </CardFooter>
  </Card>
);

// ─── Main Page ──────────────────────────────────────────────────────────────────

const InfrastructureConfigPage: React.FC = () => {
  const [configs, setConfigs] = useState<Record<InfrastructureServiceType, { config: InfrastructureConfig | null; source: 'database' | 'environment' }>>({
    clickhouse: { config: null, source: 'environment' },
    spark: { config: null, source: 'environment' },
    ollama: { config: null, source: 'environment' },
  });
  const [testResults, setTestResults] = useState<Record<InfrastructureServiceType, InfrastructureConfigTestResult | null>>({
    clickhouse: null,
    spark: null,
    ollama: null,
  });
  const [testingServices, setTestingServices] = useState<Set<InfrastructureServiceType>>(new Set());
  const [editingService, setEditingService] = useState<InfrastructureServiceType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load all configurations
  const loadConfigs = useCallback(async (showRefresh = false) => {
    if (showRefresh) setIsRefreshing(true); else setIsLoading(true);
    try {
      const allConfigs = await infrastructureService.getAllActiveConfigs();
      const newConfigs: typeof configs = {
        clickhouse: { config: null, source: 'environment' },
        spark: { config: null, source: 'environment' },
        ollama: { config: null, source: 'environment' },
      };

      for (const [type, response] of Object.entries(allConfigs)) {
        if (response && type in newConfigs) {
          newConfigs[type as InfrastructureServiceType] = {
            config: response.config,
            source: response.source || 'environment',
          };
        }
      }

      setConfigs(newConfigs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configurations');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  // Test a service connection
  const handleTest = async (serviceType: InfrastructureServiceType) => {
    setTestingServices(prev => new Set([...prev, serviceType]));
    try {
      const config = configs[serviceType].config;
      let result: InfrastructureConfigTestResult;

      if (config?.id) {
        result = await infrastructureService.testConnection({ config_id: config.id });
      } else {
        result = await infrastructureService.testConnection({
          service_type: serviceType,
          host: config?.host || 'localhost',
          port: config?.port || infrastructureService.getDefaultPort(serviceType),
          settings: config?.settings || infrastructureService.getDefaultSettings(serviceType),
        });
      }

      setTestResults(prev => ({ ...prev, [serviceType]: result }));
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [serviceType]: {
          success: false,
          message: err instanceof Error ? err.message : 'Test failed',
        },
      }));
    } finally {
      setTestingServices(prev => {
        const next = new Set(prev);
        next.delete(serviceType);
        return next;
      });
    }
  };

  const handleTestAll = async () => {
    await Promise.all(SERVICE_TYPES.map(s => handleTest(s)));
  };

  const handleSave = async (config: InfrastructureConfigCreate) => {
    const serviceType = config.service_type;
    const existingConfig = configs[serviceType].config;

    if (existingConfig?.id) {
      await infrastructureService.updateConfig(existingConfig.id, {
        name: config.name,
        description: config.description,
        host: config.host,
        port: config.port,
        settings: config.settings,
        is_active: config.is_active,
      });
    } else {
      await infrastructureService.createConfig(config);
    }

    setEditingService(null);
    await loadConfigs(true);
  };

  const handleFormTest = async (config: Partial<InfrastructureConfigCreate>): Promise<InfrastructureConfigTestResult> => {
    return infrastructureService.testConnection({
      service_type: config.service_type,
      host: config.host,
      port: config.port,
      settings: config.settings,
    });
  };

  // ── Quick stats ──────────────────────────────────────────────────────────
  const connectedCount = SERVICE_TYPES.filter(s => testResults[s]?.success).length;
  const testedCount = SERVICE_TYPES.filter(s => testResults[s] !== null).length;

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Infrastructure</h1>
            <p className="text-muted-foreground mt-1">
              Manage connections to your core infrastructure services.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadConfigs(true)}
                  disabled={isRefreshing}
                >
                  <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reload all configurations</TooltipContent>
            </Tooltip>
            <Button
              size="sm"
              onClick={handleTestAll}
              disabled={testingServices.size > 0}
            >
              <Zap className="h-4 w-4" />
              Test All
            </Button>
          </div>
        </div>

        {/* ── Stats bar ───────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Services</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{SERVICE_TYPES.length}</div>
              <p className="text-xs text-muted-foreground">Configured services</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Connected</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {testedCount > 0 ? `${connectedCount}/${testedCount}` : '—'}
              </div>
              <p className="text-xs text-muted-foreground">
                {testedCount > 0 ? 'Passed connectivity test' : 'Run tests to check'}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {testedCount === 0
                  ? '—'
                  : connectedCount === SERVICE_TYPES.length
                    ? 'Healthy'
                    : connectedCount > 0
                      ? 'Partial'
                      : 'Down'}
              </div>
              <p className="text-xs text-muted-foreground">Overall health</p>
            </CardContent>
          </Card>
        </div>

        {/* ── Error alert ─────────────────────────────────────────── */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30 p-4 flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-700 dark:text-red-300">Configuration Error</p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-0.5">{error}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setError(null)} className="shrink-0 text-red-600 hover:text-red-700">
              Dismiss
            </Button>
          </div>
        )}

        {/* ── Service cards ───────────────────────────────────────── */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {SERVICE_TYPES.map(serviceType => (
              <ServiceCard
                key={serviceType}
                serviceType={serviceType}
                config={configs[serviceType].config}
                source={configs[serviceType].source}
                testResult={testResults[serviceType]}
                isTesting={testingServices.has(serviceType)}
                onEdit={() => setEditingService(serviceType)}
                onTest={() => handleTest(serviceType)}
              />
            ))}
          </div>
        )}

        {/* ── Configuration dialog ────────────────────────────────── */}
        {editingService && (
          <ConfigDialog
            open
            serviceType={editingService}
            existingConfig={configs[editingService].config}
            onSave={handleSave}
            onClose={() => setEditingService(null)}
            onTest={handleFormTest}
          />
        )}
      </div>
    </TooltipProvider>
  );
};

export default InfrastructureConfigPage;
