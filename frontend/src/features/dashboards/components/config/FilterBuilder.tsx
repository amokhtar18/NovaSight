/**
 * Filter Builder Component
 */

import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Filter, FilterOperator } from '@/types/dashboard'

interface FilterBuilderProps {
  filters: Filter[]
  dimensions: Array<{ name: string; label: string }>
  onChange: (filters: Filter[]) => void
}

const OPERATORS: { value: FilterOperator; label: string }[] = [
  { value: 'eq', label: 'Equals' },
  { value: 'ne', label: 'Not Equals' },
  { value: 'gt', label: 'Greater Than' },
  { value: 'gte', label: 'Greater Than or Equal' },
  { value: 'lt', label: 'Less Than' },
  { value: 'lte', label: 'Less Than or Equal' },
  { value: 'in', label: 'In' },
  { value: 'not_in', label: 'Not In' },
  { value: 'contains', label: 'Contains' },
  { value: 'starts_with', label: 'Starts With' },
  { value: 'ends_with', label: 'Ends With' },
]

export function FilterBuilder({ filters, dimensions, onChange }: FilterBuilderProps) {
  const addFilter = () => {
    onChange([
      ...filters,
      { field: dimensions[0]?.name || '', operator: 'eq', value: '' },
    ])
  }
  
  const removeFilter = (index: number) => {
    onChange(filters.filter((_, i) => i !== index))
  }
  
  const updateFilter = (index: number, updates: Partial<Filter>) => {
    const newFilters = [...filters]
    newFilters[index] = { ...newFilters[index], ...updates }
    onChange(newFilters)
  }
  
  return (
    <div className="space-y-2">
      {filters.map((filter, index) => (
        <div key={index} className="flex items-center gap-2 p-2 border rounded-md">
          <Select
            value={filter.field}
            onValueChange={(value) => updateFilter(index, { field: value })}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Select field" />
            </SelectTrigger>
            <SelectContent>
              {dimensions.map((dim) => (
                <SelectItem key={dim.name} value={dim.name}>
                  {dim.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select
            value={filter.operator}
            onValueChange={(value) => updateFilter(index, { operator: value as FilterOperator })}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {OPERATORS.map((op) => (
                <SelectItem key={op.value} value={op.value}>
                  {op.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Input
            value={filter.value}
            onChange={(e) => updateFilter(index, { value: e.target.value })}
            placeholder="Value"
            className="flex-1"
          />
          
          <Button
            variant="ghost"
            size="icon"
            onClick={() => removeFilter(index)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}
      
      <Button
        variant="outline"
        size="sm"
        onClick={addFilter}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Filter
      </Button>
    </div>
  )
}
