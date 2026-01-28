/**
 * Model Card Component
 * Displays a semantic model in a card format
 */

import { Link } from 'react-router-dom'
import { MoreHorizontal, Layers, Hash, Calendar, Trash2, Edit, Copy, Eye } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { SemanticModel } from '../types'

interface ModelCardProps {
  model: SemanticModel
  compact?: boolean
  onEdit?: (model: SemanticModel) => void
  onDelete?: (model: SemanticModel) => void
  onDuplicate?: (model: SemanticModel) => void
}

const modelTypeIcons: Record<string, React.ReactNode> = {
  fact: <Layers className="h-4 w-4" />,
  dimension: <Hash className="h-4 w-4" />,
  aggregate: <Calendar className="h-4 w-4" />,
  view: <Eye className="h-4 w-4" />,
}

const modelTypeColors: Record<string, string> = {
  fact: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  dimension: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  aggregate: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  view: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
}

export function ModelCard({ model, compact = false, onEdit, onDelete, onDuplicate }: ModelCardProps) {
  if (compact) {
    // Compact/list view
    return (
      <Card className={`hover:shadow-md transition-shadow ${!model.is_active ? 'opacity-60' : ''}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <Badge variant="secondary" className={modelTypeColors[model.model_type]}>
                {modelTypeIcons[model.model_type]}
              </Badge>
              <div className="min-w-0">
                <div className="font-medium truncate">{model.label || model.name}</div>
                <div className="text-sm text-muted-foreground truncate">{model.dbt_model}</div>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>{model.dimensions_count || model.dimensions?.length || 0} dims</span>
              <span>{model.measures_count || model.measures?.length || 0} measures</span>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <Card className={`hover:shadow-md transition-shadow ${!model.is_active ? 'opacity-60' : ''}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1 min-w-0">
            <Link to={`/semantic/models/${model.id}`}>
              <CardTitle className="text-lg hover:text-primary transition-colors truncate">
                {model.label || model.name}
              </CardTitle>
            </Link>
            <CardDescription className="truncate">
              {model.dbt_model}
            </CardDescription>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit?.(model)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDuplicate?.(model)}>
                <Copy className="h-4 w-4 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => onDelete?.(model)}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-3">
          {/* Model Type Badge */}
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className={modelTypeColors[model.model_type]}>
              {modelTypeIcons[model.model_type]}
              <span className="ml-1 capitalize">{model.model_type}</span>
            </Badge>
            {!model.is_active && (
              <Badge variant="outline">Inactive</Badge>
            )}
            {model.cache_enabled && (
              <Badge variant="outline" className="text-xs">
                Cached
              </Badge>
            )}
          </div>
          
          {/* Description */}
          {model.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {model.description}
            </p>
          )}
          
          {/* Stats */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Hash className="h-3.5 w-3.5" />
              <span>{model.dimensions_count ?? model.dimensions?.length ?? 0} dimensions</span>
            </div>
            <div className="flex items-center gap-1">
              <Layers className="h-3.5 w-3.5" />
              <span>{model.measures_count ?? model.measures?.length ?? 0} measures</span>
            </div>
          </div>
          
          {/* Tags */}
          {model.tags && model.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {model.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {model.tags.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{model.tags.length - 3}
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
