/**
 * JoinBuilder — visual join configurator.
 *
 * Lets users add ref() joins to upstream dbt models, pick columns,
 * and specify join conditions using dropdowns.
 */

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent } from '@/components/ui/card'
import { Plus, Trash2, Link2 } from 'lucide-react'
import type { VisualJoinConfig } from '../../types/visualModel'

type JoinType = 'inner' | 'left' | 'right' | 'full' | 'cross'

export interface JoinBuilderProps {
  availableModels: string[]
  joins: VisualJoinConfig[]
  onChange: (joins: VisualJoinConfig[]) => void
  /**
   * Columns available on the LEFT side of every join — i.e. the
   * columns of the model's primary source (source table or first
   * ref()). Used to populate the ``Left Column`` dropdown.
   */
  leftColumns?: string[]
  /**
   * Map of model name → columns. Used to populate the ``Right Column``
   * dropdown for each join based on the selected ``source_model``.
   */
  columnsByModel?: Record<string, Array<{ name: string; type?: string; comment?: string }>>
}

const JOIN_LABELS: Record<JoinType, string> = {
  inner: 'INNER JOIN',
  left: 'LEFT JOIN',
  right: 'RIGHT JOIN',
  full: 'FULL OUTER JOIN',
  cross: 'CROSS JOIN',
}

function emptyJoin(): VisualJoinConfig {
  return {
    source_model: '',
    join_type: 'left',
    left_key: '',
    right_key: '',
  }
}

export function JoinBuilder({
  availableModels,
  joins,
  onChange,
  leftColumns = [],
  columnsByModel = {},
}: JoinBuilderProps) {
  const addJoin = () => onChange([...joins, emptyJoin()])

  const updateJoin = (index: number, partial: Partial<VisualJoinConfig>) => {
    const next = [...joins]
    next[index] = { ...next[index], ...partial }
    onChange(next)
  }

  const removeJoin = (index: number) => {
    onChange(joins.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-3">
      {joins.length === 0 ? (
        <div className="text-center py-6 text-muted-foreground text-sm border border-dashed rounded-md">
          <Link2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p>No joins configured.</p>
          <p className="text-xs mt-1">Add a join to combine data from upstream models.</p>
        </div>
      ) : (
        joins.map((join, idx) => (
          <Card key={idx} className="border-l-4 border-l-blue-400">
            <CardContent className="pt-3 pb-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">
                  Join #{idx + 1}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-destructive"
                  onClick={() => removeJoin(idx)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {/* Join Type */}
                <div className="space-y-1">
                  <Label className="text-xs">Type</Label>
                  <Select
                    value={join.join_type}
                    onValueChange={(v) => updateJoin(idx, { join_type: v as JoinType })}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(JOIN_LABELS).map(([v, label]) => (
                        <SelectItem key={v} value={v} className="text-xs">
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Source Model */}
                <div className="space-y-1">
                  <Label className="text-xs">Model (ref)</Label>
                  {availableModels.length > 0 ? (
                    <Select
                      value={join.source_model}
                      onValueChange={(v) => updateJoin(idx, { source_model: v })}
                    >
                      <SelectTrigger className="h-8 text-xs font-mono">
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableModels.map((m) => (
                          <SelectItem key={m} value={m} className="text-xs font-mono">
                            {m}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      value={join.source_model}
                      onChange={(e) => updateJoin(idx, { source_model: e.target.value })}
                      placeholder="stg_customers"
                      className="h-8 text-xs font-mono"
                    />
                  )}
                </div>
              </div>

              {/* Join Condition */}
              {join.join_type !== 'cross' && (
                <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-end">
                  <div className="space-y-1">
                    <Label className="text-xs">Left Column</Label>
                    {leftColumns.length > 0 ? (
                      <Select
                        value={join.left_key || undefined}
                        onValueChange={(v) => updateJoin(idx, { left_key: v })}
                      >
                        <SelectTrigger className="h-8 text-xs font-mono">
                          <SelectValue placeholder="Select column" />
                        </SelectTrigger>
                        <SelectContent>
                          {leftColumns.map((col) => (
                            <SelectItem
                              key={col}
                              value={col}
                              className="text-xs font-mono"
                            >
                              {col}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={join.left_key}
                        onChange={(e) => updateJoin(idx, { left_key: e.target.value })}
                        placeholder="customer_id"
                        className="h-8 text-xs font-mono"
                      />
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground pb-2">=</span>
                  <div className="space-y-1">
                    <Label className="text-xs">Right Column</Label>
                    {(() => {
                      const rightCols =
                        join.source_model && columnsByModel[join.source_model]
                          ? columnsByModel[join.source_model]!.map((c) => c.name)
                          : []
                      if (rightCols.length > 0) {
                        return (
                          <Select
                            value={join.right_key || undefined}
                            onValueChange={(v) => updateJoin(idx, { right_key: v })}
                          >
                            <SelectTrigger className="h-8 text-xs font-mono">
                              <SelectValue placeholder="Select column" />
                            </SelectTrigger>
                            <SelectContent>
                              {rightCols.map((col) => (
                                <SelectItem
                                  key={col}
                                  value={col}
                                  className="text-xs font-mono"
                                >
                                  {col}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )
                      }
                      return (
                        <Input
                          value={join.right_key}
                          onChange={(e) => updateJoin(idx, { right_key: e.target.value })}
                          placeholder={join.source_model ? 'id' : 'pick a model first'}
                          className="h-8 text-xs font-mono"
                          disabled={!join.source_model}
                        />
                      )
                    })()}
                  </div>
                </div>
              )}

              {/* Additional conditions */}
              {join.additional_conditions && join.additional_conditions.length > 0 && (
                <div className="space-y-1">
                  <Label className="text-xs">Additional ON Conditions</Label>
                  {join.additional_conditions.map((cond, cIdx) => (
                    <div key={cIdx} className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">AND</span>
                      <Input
                        value={cond}
                        onChange={(e) => {
                          const updated = [...(join.additional_conditions || [])]
                          updated[cIdx] = e.target.value
                          updateJoin(idx, { additional_conditions: updated })
                        }}
                        placeholder="left.col = right.col"
                        className="h-7 text-xs font-mono flex-1"
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => {
                          const updated = (join.additional_conditions || []).filter((_, i) => i !== cIdx)
                          updateJoin(idx, { additional_conditions: updated })
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-6"
                onClick={() => {
                  updateJoin(idx, {
                    additional_conditions: [...(join.additional_conditions || []), ''],
                  })
                }}
              >
                <Plus className="h-3 w-3 mr-1" />
                Add condition
              </Button>
            </CardContent>
          </Card>
        ))
      )}

      <Button variant="outline" size="sm" onClick={addJoin} className="w-full">
        <Plus className="h-3.5 w-3.5 mr-1" />
        Add Join
      </Button>
    </div>
  )
}
