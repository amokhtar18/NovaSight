/**
 * Query Configuration Editor
 */

import { useQuery } from '@tanstack/react-query'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import api from '@/lib/api'
import { FilterBuilder } from './FilterBuilder'
import type { QueryConfig, Filter } from '@/types/dashboard'

interface QueryConfigEditorProps {
  config: QueryConfig
  onChange: (config: QueryConfig) => void
}

interface SemanticModel {
  name: string
  dimensions: Array<{ name: string; label: string }>
  measures: Array<{ name: string; label: string }>
}

export function QueryConfigEditor({ config, onChange }: QueryConfigEditorProps) {
  const { data: models } = useQuery({
    queryKey: ['semantic-models'],
    queryFn: async () => {
      const response = await api.get<SemanticModel[]>('/semantic/models')
      return response.data
    },
  })
  
  const allDimensions = models?.flatMap((m: SemanticModel) => m.dimensions) || []
  const allMeasures = models?.flatMap((m: SemanticModel) => m.measures) || []
  
  const handleDimensionToggle = (dimName: string) => {
    const newDims = config.dimensions.includes(dimName)
      ? config.dimensions.filter(d => d !== dimName)
      : [...config.dimensions, dimName]
    onChange({ ...config, dimensions: newDims })
  }
  
  const handleMeasureToggle = (measureName: string) => {
    const newMeasures = config.measures.includes(measureName)
      ? config.measures.filter(m => m !== measureName)
      : [...config.measures, measureName]
    onChange({ ...config, measures: newMeasures })
  }
  
  return (
    <div className="space-y-4">
      <div>
        <Label>Dimensions</Label>
        <div className="mt-2 space-y-2 max-h-40 overflow-y-auto border rounded-md p-2">
          {allDimensions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No dimensions available</p>
          ) : (
            allDimensions.map((dim: { name: string; label: string }) => (
              <label key={dim.name} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.dimensions.includes(dim.name)}
                  onChange={() => handleDimensionToggle(dim.name)}
                  className="rounded"
                />
                <span className="text-sm">{dim.label}</span>
              </label>
            ))
          )}
        </div>
      </div>
      
      <div>
        <Label>Measures</Label>
        <div className="mt-2 space-y-2 max-h-40 overflow-y-auto border rounded-md p-2">
          {allMeasures.length === 0 ? (
            <p className="text-sm text-muted-foreground">No measures available</p>
          ) : (
            allMeasures.map((measure: { name: string; label: string }) => (
              <label key={measure.name} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.measures.includes(measure.name)}
                  onChange={() => handleMeasureToggle(measure.name)}
                  className="rounded"
                />
                <span className="text-sm">{measure.label}</span>
              </label>
            ))
          )}
        </div>
      </div>
      
      <div>
        <Label>Filters</Label>
        <FilterBuilder
          filters={config.filters || []}
          dimensions={allDimensions}
          onChange={(filters: Filter[]) => onChange({ ...config, filters })}
        />
      </div>
      
      <div>
        <Label htmlFor="limit">Limit</Label>
        <Input
          id="limit"
          type="number"
          value={config.limit || 100}
          onChange={(e) => onChange({ ...config, limit: parseInt(e.target.value) || 100 })}
          min={1}
          max={10000}
        />
      </div>
    </div>
  )
}
