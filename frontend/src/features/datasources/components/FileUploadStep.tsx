/**
 * FileUploadStep
 * ──────────────
 * Drag-and-drop file upload step used inside the ConnectionWizard for
 * flat-file, Excel, and SQLite data sources.
 *
 * Flow:
 *   1. User selects/drops a file
 *   2. POST multipart/form-data → /api/v1/connections/uploads
 *   3. Backend validates, stores, introspects and returns an upload_token
 *   4. This component surfaces introspection results and calls onUploadComplete
 *      so the wizard can proceed to the naming step.
 */

import { useCallback, useRef, useState } from 'react'
import { Upload, FileText, CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { apiClient, ApiError } from '@/services/apiClient'
import type { DatabaseType, FileUploadMetadata } from '@/types/datasource'
import { DATABASE_TYPES } from '@/types/datasource'

const MAX_SIZE_BYTES = 200 * 1024 * 1024 // 200 MB

interface FileUploadStepProps {
  dbType: DatabaseType
  onUploadComplete: (meta: FileUploadMetadata) => void
  uploadedMeta: FileUploadMetadata | null
}

type UploadState =
  | { status: 'idle' }
  | { status: 'uploading'; progress: number }
  | { status: 'success'; meta: FileUploadMetadata }
  | { status: 'error'; message: string }

export function FileUploadStep({ dbType, onUploadComplete, uploadedMeta }: FileUploadStepProps) {
  const [uploadState, setUploadState] = useState<UploadState>(
    uploadedMeta ? { status: 'success', meta: uploadedMeta } : { status: 'idle' }
  )
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const typeInfo = DATABASE_TYPES[dbType]

  const accept = typeInfo?.acceptedExtensions?.join(',') ?? '*'

  const handleFile = useCallback(
    async (file: File) => {
      // Client-side size guard
      if (file.size > MAX_SIZE_BYTES) {
        setUploadState({
          status: 'error',
          message: `File exceeds the 200 MB size limit (${(file.size / 1024 / 1024).toFixed(1)} MB)`,
        })
        return
      }

      setUploadState({ status: 'uploading', progress: 0 })

      const formData = new FormData()
      formData.append('file', file)
      formData.append('db_type', dbType)

      try {
        const { data: json } = await apiClient.post(
          '/api/v1/connections/uploads',
          formData,
          {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120_000,
          }
        )

        const md = json.metadata ?? {}
        const meta: FileUploadMetadata = {
          file_ref: json.file_id ?? json.file_ref ?? '',
          file_hash: md.file_hash ?? json.file_hash ?? '',
          file_name: md.original_filename ?? json.file_name ?? file.name,
          file_size: md.size_bytes ?? json.file_size ?? file.size,
          file_format: md.format ?? json.file_format ?? '',
          upload_token: json.upload_token,
          introspection: json.introspection ?? {
            columns: json.columns,
            preview_rows: json.preview_rows,
            sheets: json.sheets,
            tables: json.tables,
          },
        }

        setUploadState({ status: 'success', meta })
        onUploadComplete(meta)
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Upload failed'
        setUploadState({ status: 'error', message })
      }
    },
    [dbType, onUploadComplete]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files?.[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    // Reset input so the same file can be re-selected if needed
    e.target.value = ''
  }

  const reset = () => setUploadState({ status: 'idle' })

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-1">Upload File</h3>
        <p className="text-sm text-muted-foreground">
          Upload a {typeInfo?.name} file (max 200 MB).
          Accepted formats:{' '}
          <span className="font-mono">{typeInfo?.acceptedExtensions?.join(', ')}</span>
        </p>
      </div>

      {/* Drop zone */}
      {uploadState.status !== 'success' && (
        <div
          className={cn(
            'relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 text-center transition-colors',
            dragOver
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25 hover:border-primary/50',
            uploadState.status === 'uploading' && 'pointer-events-none opacity-60'
          )}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          {uploadState.status === 'uploading' ? (
            <Loader2 className="h-10 w-10 animate-spin text-primary mb-3" />
          ) : (
            <Upload className="h-10 w-10 text-muted-foreground mb-3" />
          )}

          <p className="text-sm font-medium mb-1">
            {uploadState.status === 'uploading'
              ? 'Uploading and validating…'
              : 'Drag & drop your file here'}
          </p>
          <p className="text-xs text-muted-foreground mb-4">or click to browse</p>

          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={uploadState.status === 'uploading'}
            onClick={() => fileInputRef.current?.click()}
          >
            Browse
          </Button>

          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            className="sr-only"
            onChange={handleInputChange}
          />
        </div>
      )}

      {/* Error state */}
      {uploadState.status === 'error' && (
        <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <XCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-destructive">Upload failed</p>
            <p className="text-sm text-destructive/80 mt-0.5">{uploadState.message}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={reset}>
            Try again
          </Button>
        </div>
      )}

      {/* Success state */}
      {uploadState.status === 'success' && (
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg border border-green-500/30 bg-green-500/10 p-4">
            <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-700 dark:text-green-400">
                File uploaded and validated
              </p>
              <div className="text-xs text-muted-foreground mt-1 space-y-0.5">
                <p><span className="font-medium">Name:</span> {uploadState.meta.file_name}</p>
                <p><span className="font-medium">Format:</span> {uploadState.meta.file_format?.toUpperCase()}</p>
                <p>
                  <span className="font-medium">Size:</span>{' '}
                  {(uploadState.meta.file_size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={reset}>
              Replace
            </Button>
          </div>

          <IntrospectionPreview meta={uploadState.meta} />
        </div>
      )}
    </div>
  )
}

/** Shows a summary of columns / sheets / tables from the introspection result. */
function IntrospectionPreview({ meta }: { meta: FileUploadMetadata }) {
  const intro = meta.introspection

  if (intro.sheets && intro.sheets.length > 0) {
    return (
      <div className="rounded-lg border p-4 space-y-3">
        <p className="text-sm font-medium">Sheets found ({intro.sheets.length})</p>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {intro.sheets.map((s) => (
            <div key={s.name} className="text-xs border rounded p-2">
              <span className="font-mono font-medium">{s.name}</span>
              <span className="text-muted-foreground ml-2">
                {s.columns.length} column{s.columns.length !== 1 ? 's' : ''}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (intro.tables && intro.tables.length > 0) {
    return (
      <div className="rounded-lg border p-4 space-y-3">
        <p className="text-sm font-medium">Tables found ({intro.tables.length})</p>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {intro.tables.map((t) => (
            <div key={t.name} className="text-xs border rounded p-2">
              <span className="font-mono font-medium">{t.name}</span>
              <span className="text-muted-foreground ml-2">
                {t.row_count?.toLocaleString() ?? '?'} rows &middot; {t.columns.length} columns
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (intro.columns && intro.columns.length > 0) {
    return (
      <div className="rounded-lg border p-4 space-y-3">
        <p className="text-sm font-medium">Columns detected ({intro.columns.length})</p>
        <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
          {intro.columns.map((c) => (
            <span key={c.name} className="text-xs font-mono bg-muted px-2 py-0.5 rounded">
              {c.name}
              <span className="text-muted-foreground ml-1">:{c.data_type}</span>
            </span>
          ))}
        </div>
      </div>
    )
  }

  return null
}
