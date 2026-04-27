/**
 * Pipeline Wizard – Step 1: Source Kind Picker
 * ---------------------------------------------
 * Lets the user choose between a SQL database connection and an uploaded
 * file as the source for the pipeline.
 */

import { Database, FileSpreadsheet } from 'lucide-react'
import { Card } from '@/components/ui/card'
import type { SourceKind, WizardState } from '@/types/pipeline'

interface SourceKindStepProps {
  state: WizardState
  onStateChange: (updates: Partial<WizardState>) => void
}

interface KindOption {
  value: SourceKind
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
}

const OPTIONS: KindOption[] = [
  {
    value: 'sql',
    title: 'Database Connection',
    description:
      'Pull from a registered SQL database (PostgreSQL, MySQL, Oracle, ClickHouse, etc.).',
    icon: Database,
  },
  {
    value: 'file',
    title: 'File Upload',
    description:
      'Upload a flat-file or spreadsheet (CSV, TSV, XLSX, Parquet, JSON, JSONL).',
    icon: FileSpreadsheet,
  },
]

export function SourceKindStep({ state, onStateChange }: SourceKindStepProps) {
  const choose = (kind: SourceKind) => {
    if (state.sourceKind === kind) return
    // Reset incompatible fields when switching kinds
    if (kind === 'sql') {
      onStateChange({
        sourceKind: 'sql',
        fileFormat: undefined,
        fileObjectKey: undefined,
        fileOriginalName: undefined,
        fileSizeBytes: undefined,
        fileOptions: {},
        columnsConfig: [],
      })
    } else {
      onStateChange({
        sourceKind: 'file',
        connectionId: undefined,
        sourceSchema: undefined,
        sourceTable: undefined,
        sourceQuery: undefined,
        sourceType: 'table',
        columnsConfig: [],
      })
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Choose source type</h3>
        <p className="text-sm text-muted-foreground">
          Pick where your pipeline will read data from.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {OPTIONS.map((opt) => {
          const Icon = opt.icon
          const selected = state.sourceKind === opt.value
          return (
            <Card
              key={opt.value}
              role="button"
              tabIndex={0}
              onClick={() => choose(opt.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  choose(opt.value)
                }
              }}
              className={`p-6 cursor-pointer transition-colors ${
                selected
                  ? 'border-primary ring-2 ring-primary/30'
                  : 'hover:border-primary/40'
              }`}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`rounded-lg p-3 ${
                    selected
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  <Icon className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="font-semibold">{opt.title}</p>
                  <p className="text-sm text-muted-foreground">{opt.description}</p>
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
