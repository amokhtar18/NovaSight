/**
 * Semantic Models List Page
 * Main page for viewing and managing semantic models
 */

import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Filter, LayoutGrid, LayoutList, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ModelCard } from '../components/ModelCard'
import { CreateModelDialog } from '../components/CreateModelDialog'
import { useSemanticModels } from '../hooks/useSemanticModels'
import type { SemanticModel, ModelType } from '../types'

type ViewMode = 'grid' | 'list'
type FilterType = 'all' | ModelType
type ModelCounts = { dimension: number; fact: number; aggregate: number; view: number }

export function SemanticModelsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<FilterType>('all')
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  
  const { data: models, isLoading, refetch, isRefetching } = useSemanticModels()
  
  const filteredModels = useMemo(() => {
    if (!models) return []
    
    let result = models as SemanticModel[]
    
    // Filter by type
    if (filterType !== 'all') {
      result = result.filter((m: SemanticModel) => m.model_type === filterType)
    }
    
    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter((m: SemanticModel) => 
        m.name.toLowerCase().includes(query) ||
        m.label?.toLowerCase().includes(query) ||
        m.description?.toLowerCase().includes(query) ||
        m.tags?.some((t: string) => t.toLowerCase().includes(query))
      )
    }
    
    return result
  }, [models, filterType, searchQuery])
  
  // Group models by type for summary
  const modelCounts = useMemo((): ModelCounts => {
    if (!models) return { dimension: 0, fact: 0, aggregate: 0, view: 0 }
    
    return (models as SemanticModel[]).reduce((acc: ModelCounts, m: SemanticModel) => {
      const key = m.model_type as keyof ModelCounts
      if (key in acc) {
        acc[key] = acc[key] + 1
      }
      return acc
    }, { dimension: 0, fact: 0, aggregate: 0, view: 0 })
  }, [models])
  
  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Semantic Layer</h1>
          <p className="text-muted-foreground mt-1">
            Define and manage semantic models for your data
          </p>
        </div>
        
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Model
        </Button>
      </div>
      
      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard 
          label="Dimension Models" 
          count={modelCounts.dimension} 
          color="blue" 
        />
        <StatCard 
          label="Fact Models" 
          count={modelCounts.fact} 
          color="green" 
        />
        <StatCard 
          label="Aggregate Models" 
          count={modelCounts.aggregate} 
          color="purple" 
        />
        <StatCard 
          label="View Models" 
          count={modelCounts.view} 
          color="orange" 
        />
      </div>
      
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search models..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <Select value={filterType} onValueChange={(v) => setFilterType(v as FilterType)}>
            <SelectTrigger className="w-40">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="dimension">Dimension</SelectItem>
              <SelectItem value="fact">Fact</SelectItem>
              <SelectItem value="aggregate">Aggregate</SelectItem>
              <SelectItem value="view">View</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="icon"
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            <RefreshCw className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
          </Button>
          <div className="border rounded-md flex">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('grid')}
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('list')}
            >
              <LayoutList className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
      
      {/* Models Grid/List */}
      {isLoading ? (
        <div className={
          viewMode === 'grid' 
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'space-y-3'
        }>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      ) : filteredModels.length === 0 ? (
        <div className="text-center py-12">
          {models?.length === 0 ? (
            <>
              <h3 className="text-lg font-medium">No semantic models yet</h3>
              <p className="text-muted-foreground mt-1">
                Create your first semantic model to get started
              </p>
              <Button 
                className="mt-4" 
                onClick={() => setCreateDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Model
              </Button>
            </>
          ) : (
            <>
              <h3 className="text-lg font-medium">No models found</h3>
              <p className="text-muted-foreground mt-1">
                Try adjusting your search or filter criteria
              </p>
            </>
          )}
        </div>
      ) : (
        <div className={
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'space-y-3'
        }>
          {filteredModels.map((model: SemanticModel) => (
            <Link key={model.id} to={`/semantic/models/${model.id}`}>
              <ModelCard model={model} compact={viewMode === 'list'} />
            </Link>
          ))}
        </div>
      )}
      
      {/* Create Model Dialog */}
      <CreateModelDialog 
        open={createDialogOpen} 
        onClose={() => setCreateDialogOpen(false)} 
      />
    </div>
  )
}

interface StatCardProps {
  label: string
  count: number
  color: 'blue' | 'green' | 'purple' | 'orange'
}

function StatCard({ label, count, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
    orange: 'bg-orange-50 border-orange-200 text-orange-700',
  }
  
  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <div className="text-2xl font-bold">{count}</div>
      <div className="text-sm opacity-80">{label}</div>
    </div>
  )
}
