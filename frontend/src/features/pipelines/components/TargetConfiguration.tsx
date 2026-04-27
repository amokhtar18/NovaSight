/**
 * Pipeline Wizard - Step 3: Target Configuration
 */

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Database, History, Merge, Replace, ArrowRightCircle, AlertTriangle } from 'lucide-react'
import type { WizardState, WriteDisposition, IncrementalCursorType, WRITE_DISPOSITION_OPTIONS, INCREMENTAL_TYPE_OPTIONS } from '@/types/pipeline'

interface TargetConfigurationProps {
  state: WizardState
  onStateChange: (updates: Partial<WizardState>) => void
}

const WRITE_DISPOSITIONS: { value: WriteDisposition; label: string; description: string; icon: React.ReactNode }[] = [
  {
    value: 'append',
    label: 'Append',
    description: 'Add new rows to existing data. Simple and fast.',
    icon: <ArrowRightCircle className="h-5 w-5" />,
  },
  {
    value: 'replace',
    label: 'Replace',
    description: 'Drop and recreate the table each run. Use for small dimension tables.',
    icon: <Replace className="h-5 w-5" />,
  },
  {
    value: 'merge',
    label: 'Merge (Upsert)',
    description: 'Update existing rows, insert new ones. Requires primary key.',
    icon: <Merge className="h-5 w-5" />,
  },
  {
    value: 'scd2',
    label: 'SCD Type 2',
    description: 'Track historical changes with validity dates. Requires primary key.',
    icon: <History className="h-5 w-5" />,
  },
]

const INCREMENTAL_TYPES: { value: IncrementalCursorType; label: string; description: string }[] = [
  { value: 'none', label: 'Full Load', description: 'Load all data each run' },
  { value: 'timestamp', label: 'Timestamp Column', description: 'Incremental by timestamp/datetime' },
  { value: 'version', label: 'Version Column', description: 'Incremental by version number' },
]

// Must match the keys of PRESET_TO_CRON in
// backend/orchestration/schedules/dlt_schedules.py
type SchedulePresetValue =
  | 'manual'
  | 'every_15_min'
  | 'every_30_min'
  | 'hourly'
  | 'every_6_hours'
  | 'every_12_hours'
  | 'daily'
  | 'weekly'
  | 'monthly'
  | 'custom'

const SCHEDULE_PRESETS: { value: SchedulePresetValue; label: string; description: string }[] = [
  { value: 'manual', label: 'Manual', description: 'No schedule — run on demand only' },
  { value: 'every_15_min', label: 'Every 15 minutes', description: 'High-frequency near-real-time loads' },
  { value: 'every_30_min', label: 'Every 30 minutes', description: 'Frequent incremental loads' },
  { value: 'hourly', label: 'Hourly', description: 'Top of every hour' },
  { value: 'every_6_hours', label: 'Every 6 hours', description: 'Four times a day' },
  { value: 'every_12_hours', label: 'Every 12 hours', description: 'Twice daily' },
  { value: 'daily', label: 'Daily', description: 'Once per day at midnight' },
  { value: 'weekly', label: 'Weekly', description: 'Once per week (Sunday 00:00)' },
  { value: 'monthly', label: 'Monthly', description: 'First day of every month' },
  { value: 'custom', label: 'Custom (cron)', description: 'Provide a custom cron expression' },
]

function readSchedulePreset(options: Record<string, unknown>): SchedulePresetValue {
  const preset = typeof options.schedule_preset === 'string' ? options.schedule_preset : ''
  const cron = typeof options.schedule_cron === 'string' ? options.schedule_cron : ''
  if (cron) return 'custom'
  const known = SCHEDULE_PRESETS.find((p) => p.value === preset)
  if (known) return known.value
  return 'manual'
}

export function TargetConfiguration({ state, onStateChange }: TargetConfigurationProps) {
  const requiresPrimaryKey = state.writeDisposition === 'merge' || state.writeDisposition === 'scd2'
  const hasPrimaryKey = state.primaryKeyColumns && state.primaryKeyColumns.length > 0

  const options = state.options || {}
  const schedulePreset = readSchedulePreset(options)
  const customCron =
    typeof options.schedule_cron === 'string' ? (options.schedule_cron as string) : ''

  const handleScheduleChange = (preset: SchedulePresetValue) => {
    const next: Record<string, unknown> = { ...options }
    // Reset both fields, then set whichever applies.
    delete next.schedule_preset
    delete next.schedule_cron
    if (preset === 'custom') {
      next.schedule_cron = customCron || ''
    } else if (preset !== 'manual') {
      next.schedule_preset = preset
    }
    onStateChange({ options: next })
  }

  const handleCronChange = (cron: string) => {
    const next: Record<string, unknown> = { ...options }
    delete next.schedule_preset
    if (cron) {
      next.schedule_cron = cron
    } else {
      delete next.schedule_cron
    }
    onStateChange({ options: next })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Configure Target</h3>
        <p className="text-sm text-muted-foreground">
          Configure how data is written to the Iceberg table in your data lake.
        </p>
      </div>

      {/* Pipeline Name */}
      <div className="space-y-2">
        <Label htmlFor="pipeline-name">Pipeline Name *</Label>
        <Input
          id="pipeline-name"
          value={state.name || ''}
          onChange={(e) => onStateChange({ name: e.target.value })}
          placeholder="e.g., customers_daily_sync"
          className="max-w-md"
        />
        <p className="text-xs text-muted-foreground">
          Must start with a letter and contain only letters, numbers, and underscores.
        </p>
      </div>

      {/* Description */}
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Input
          id="description"
          value={state.description || ''}
          onChange={(e) => onStateChange({ description: e.target.value })}
          placeholder="Optional description for this pipeline"
          className="max-w-md"
        />
      </div>

      {/* Write Disposition */}
      <div className="space-y-3">
        <Label>Write Disposition *</Label>
        <RadioGroup
          value={state.writeDisposition}
          onValueChange={(value: WriteDisposition) => onStateChange({ writeDisposition: value })}
          className="grid grid-cols-2 gap-4"
        >
          {WRITE_DISPOSITIONS.map((option) => (
            <div
              key={option.value}
              className={`flex items-start space-x-3 p-4 border rounded-lg cursor-pointer hover:bg-accent ${
                state.writeDisposition === option.value ? 'border-primary bg-accent' : ''
              }`}
            >
              <RadioGroupItem value={option.value} id={`wd-${option.value}`} className="mt-1" />
              <div className="flex-1">
                <Label htmlFor={`wd-${option.value}`} className="flex items-center gap-2 cursor-pointer">
                  {option.icon}
                  <span className="font-medium">{option.label}</span>
                </Label>
                <p className="text-sm text-muted-foreground mt-1">
                  {option.description}
                </p>
              </div>
            </div>
          ))}
        </RadioGroup>
      </div>

      {/* Primary Key Warning */}
      {requiresPrimaryKey && !hasPrimaryKey && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Primary Key Required</AlertTitle>
          <AlertDescription>
            {state.writeDisposition === 'merge'
              ? 'Merge requires a primary key to identify rows for upsert.'
              : 'SCD Type 2 requires a primary key to track historical changes.'}
            <br />
            Go back to Column Selection and mark one or more columns as primary key.
          </AlertDescription>
        </Alert>
      )}

      {/* Incremental Configuration */}
      <div className="space-y-3">
        <Label>Incremental Loading</Label>
        <RadioGroup
          value={state.incrementalCursorType}
          onValueChange={(value: IncrementalCursorType) => onStateChange({ incrementalCursorType: value })}
          className="space-y-2"
        >
          {INCREMENTAL_TYPES.map((option) => (
            <div
              key={option.value}
              className={`flex items-center space-x-3 p-3 border rounded-lg cursor-pointer hover:bg-accent ${
                state.incrementalCursorType === option.value ? 'border-primary bg-accent' : ''
              }`}
            >
              <RadioGroupItem value={option.value} id={`inc-${option.value}`} />
              <Label htmlFor={`inc-${option.value}`} className="flex-1 cursor-pointer">
                <span className="font-medium">{option.label}</span>
                <span className="text-muted-foreground ml-2">— {option.description}</span>
              </Label>
            </div>
          ))}
        </RadioGroup>
        
        {state.incrementalCursorType !== 'none' && state.incrementalCursorColumn && (
          <div className="flex items-center gap-2 text-sm">
            <Badge variant="secondary">Cursor Column</Badge>
            <span className="font-mono">{state.incrementalCursorColumn}</span>
          </div>
        )}
        
        {state.incrementalCursorType !== 'none' && !state.incrementalCursorColumn && (
          <Alert>
            <AlertDescription>
              Go back to Column Selection and select an incremental cursor column.
            </AlertDescription>
          </Alert>
        )}
      </div>

      {/* Schedule */}
      <div className="space-y-3">
        <Label>Schedule</Label>
        <p className="text-xs text-muted-foreground">
          Pick how often this pipeline should run. Manual pipelines do not appear in the
          scheduler — choose a preset or a custom cron to enable automatic runs.
        </p>
        <RadioGroup
          value={schedulePreset}
          onValueChange={(value: SchedulePresetValue) => handleScheduleChange(value)}
          className="grid grid-cols-2 gap-3"
        >
          {SCHEDULE_PRESETS.map((option) => (
            <div
              key={option.value}
              className={`flex items-start space-x-3 p-3 border rounded-lg cursor-pointer hover:bg-accent ${
                schedulePreset === option.value ? 'border-primary bg-accent' : ''
              }`}
            >
              <RadioGroupItem value={option.value} id={`sched-${option.value}`} className="mt-1" />
              <Label htmlFor={`sched-${option.value}`} className="flex-1 cursor-pointer">
                <span className="font-medium">{option.label}</span>
                <span className="text-muted-foreground ml-2 text-sm">— {option.description}</span>
              </Label>
            </div>
          ))}
        </RadioGroup>
        {schedulePreset === 'custom' && (
          <div className="space-y-1">
            <Label htmlFor="schedule-cron">Cron expression *</Label>
            <Input
              id="schedule-cron"
              value={customCron}
              onChange={(e) => handleCronChange(e.target.value)}
              placeholder="e.g. 0 2 * * *"
              className="max-w-xs font-mono"
            />
            <p className="text-xs text-muted-foreground">
              Standard 5-field cron (min hour day month weekday).
            </p>
          </div>
        )}
      </div>

      {/* Iceberg Table Name */}
      <div className="space-y-2">
        <Label htmlFor="iceberg-table">Iceberg Table Name (optional)</Label>
        <Input
          id="iceberg-table"
          value={state.icebergTableName || ''}
          onChange={(e) => onStateChange({ icebergTableName: e.target.value })}
          placeholder="Auto-generated from source table name"
          className="max-w-md"
        />
        <p className="text-xs text-muted-foreground">
          Leave empty to auto-generate from the source table name.
          Must be lowercase with only letters, numbers, and underscores.
        </p>
      </div>
    </div>
  )
}
