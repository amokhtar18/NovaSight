/**
 * Pipeline Wizard – File Source Selector
 * --------------------------------------
 * Allows the user to upload a flat-file or spreadsheet (CSV / TSV / XLSX /
 * XLS / Parquet / JSON / JSONL) which is streamed to the tenant's S3 bucket
 * under ``raw_uploads/<uuid>/<safe_name>``. The returned object key is then
 * referenced by a ``source_kind = 'file'`` dlt pipeline.
 */

import { useRef, useState } from 'react'
import { Upload, FileText, Loader2, Trash2, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useToast } from '@/components/ui/use-toast'
import { pipelineService } from '@/services/pipelineService'
import type {
  WizardState,
  ColumnConfig,
  FileFormat,
  FileUploadResult,
} from '@/types/pipeline'

const ACCEPTED = '.csv,.tsv,.xlsx,.xls,.parquet,.json,.jsonl,.ndjson'
const MAX_BYTES = 500 * 1024 * 1024 // 500 MB — must mirror DLT_UPLOAD_MAX_BYTES

interface FileSourceSelectorProps {
  state: WizardState
  onStateChange: (updates: Partial<WizardState>) => void
}

function humanBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}

export function FileSourceSelector({ state, onStateChange }: FileSourceSelectorProps) {
  const { toast } = useToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<FileUploadResult | null>(
    state.fileObjectKey
      ? {
          object_key: state.fileObjectKey,
          bucket: '',
          size_bytes: state.fileSizeBytes ?? 0,
          file_format: (state.fileFormat ?? 'csv') as FileFormat,
          original_filename: state.fileOriginalName ?? '',
          sheets: ((state.fileOptions?.available_sheets as string[]) ?? []),
          columns_preview: ((state.fileOptions?.columns_preview as string[]) ?? []),
          rows_preview: ((state.fileOptions?.rows_preview as Array<Record<string, unknown>>) ?? []),
        }
      : null,
  )

  const fileOpts = (state.fileOptions ?? {}) as Record<string, unknown>

  const setOpt = (patch: Record<string, unknown>) => {
    onStateChange({ fileOptions: { ...fileOpts, ...patch } })
  }

  const buildColumns = (names: string[]): ColumnConfig[] =>
    names.map((n) => ({
      name: n,
      data_type: 'VARCHAR',
      include: true,
      nullable: true,
    }))

  const handleSelect = async (file: File | null) => {
    if (!file) return
    if (file.size > MAX_BYTES) {
      toast({
        title: 'File too large',
        description: `Maximum upload size is ${humanBytes(MAX_BYTES)}.`,
        variant: 'destructive',
      })
      return
    }

    setUploading(true)
    setProgress(0)
    try {
      const r = await pipelineService.uploadFile(file, setProgress)
      setResult(r)

      // Seed wizard state with all the upload metadata + a sensible default
      // set of columns derived from the backend preview. For Excel files
      // backend defaults to the first sheet; if the user picks a different
      // sheet later we wipe columns and they re-introspect on Next.
      const defaultColumns = buildColumns(r.columns_preview)

      onStateChange({
        sourceKind: 'file',
        connectionId: undefined,
        fileFormat: r.file_format,
        fileObjectKey: r.object_key,
        fileOriginalName: r.original_filename,
        fileSizeBytes: r.size_bytes,
        fileOptions: {
          ...(state.fileOptions ?? {}),
          available_sheets: r.sheets,
          columns_preview: r.columns_preview,
          rows_preview: r.rows_preview ?? [],
          // Default sheet for Excel uploads
          ...(r.sheets.length > 0 && !state.fileOptions?.sheet_name
            ? { sheet_name: r.sheets[0] }
            : {}),
        },
        columnsConfig: defaultColumns,
      })

      toast({
        title: 'Upload complete',
        description: `${r.original_filename} (${humanBytes(r.size_bytes)})`,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      toast({ title: 'Upload failed', description: message, variant: 'destructive' })
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleRemove = async () => {
    if (!state.fileObjectKey) return
    try {
      await pipelineService.deleteUpload(state.fileObjectKey)
    } catch {
      // Non-fatal: even if delete fails on the server, drop the local ref so
      // the user can re-upload.
    }
    setResult(null)
    onStateChange({
      fileObjectKey: undefined,
      fileFormat: undefined,
      fileOriginalName: undefined,
      fileSizeBytes: undefined,
      fileOptions: {},
      columnsConfig: [],
    })
  }

  const isExcel = state.fileFormat === 'xlsx' || state.fileFormat === 'xls'
  const isCsv = state.fileFormat === 'csv' || state.fileFormat === 'tsv'

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Upload Data File</h3>
        <p className="text-sm text-muted-foreground">
          Upload a flat-file or spreadsheet. The file is stored privately in
          your tenant's object storage and ingested into Iceberg by the pipeline.
        </p>
      </div>

      {!result && (
        <div className="rounded-lg border-2 border-dashed p-8 text-center space-y-4">
          <div className="flex justify-center">
            <Upload className="h-10 w-10 text-muted-foreground" />
          </div>
          <div className="space-y-1">
            <p className="font-medium">Drag & drop or click to select a file</p>
            <p className="text-sm text-muted-foreground">
              Supported: CSV, TSV, XLSX, XLS, Parquet, JSON, JSONL · max {humanBytes(MAX_BYTES)}
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={(e) => handleSelect(e.target.files?.[0] ?? null)}
          />
          <Button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Uploading…
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Choose file
              </>
            )}
          </Button>
          {uploading && (
            <div className="max-w-sm mx-auto space-y-1">
              <Progress value={progress} className="h-2" />
              <p className="text-xs text-muted-foreground">{progress}%</p>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <FileText className="h-5 w-5 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="font-medium truncate">{result.original_filename}</p>
                <div className="flex flex-wrap gap-2 mt-1 text-xs text-muted-foreground">
                  <Badge variant="secondary" className="uppercase">
                    {result.file_format}
                  </Badge>
                  <span>{humanBytes(result.size_bytes)}</span>
                  <span className="font-mono truncate">{result.object_key}</span>
                </div>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={handleRemove}>
              <Trash2 className="h-4 w-4 mr-2" />
              Remove
            </Button>
          </div>

          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              File uploaded. Configure parsing options below, then continue.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Format-specific options */}
      {result && isCsv && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>Delimiter</Label>
            <Input
              value={(fileOpts.delimiter as string) ?? (state.fileFormat === 'tsv' ? '\\t' : ',')}
              onChange={(e) => setOpt({ delimiter: e.target.value })}
              placeholder=","
            />
          </div>
          <div className="space-y-2">
            <Label>Encoding</Label>
            <Select
              value={(fileOpts.encoding as string) ?? 'utf-8'}
              onValueChange={(v) => setOpt({ encoding: v })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="utf-8">UTF-8</SelectItem>
                <SelectItem value="utf-16">UTF-16</SelectItem>
                <SelectItem value="latin-1">Latin-1</SelectItem>
                <SelectItem value="cp1252">Windows-1252</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Header row index</Label>
            <Input
              type="number"
              min={0}
              value={(fileOpts.header_row as number) ?? 0}
              onChange={(e) => setOpt({ header_row: Number(e.target.value) })}
            />
          </div>
        </div>
      )}

      {result && isExcel && result.sheets.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Sheet</Label>
            <Select
              value={(fileOpts.sheet_name as string) ?? result.sheets[0]}
              onValueChange={(v) => {
                setOpt({ sheet_name: v })
                // Clear column config when sheet changes; user will need to
                // re-introspect via the next step. For now we wipe so they
                // can't carry stale columns from another sheet.
                onStateChange({ columnsConfig: [] })
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {result.sheets.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Header row index</Label>
            <Input
              type="number"
              min={0}
              value={(fileOpts.header_row as number) ?? 0}
              onChange={(e) => setOpt({ header_row: Number(e.target.value) })}
            />
          </div>
        </div>
      )}

      {result && isExcel && state.columnsConfig.length === 0 && (
        <Alert variant="default">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Excel sheet selected. Columns will be auto-detected when you proceed.
            For best results, ensure the chosen sheet has a header row.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
