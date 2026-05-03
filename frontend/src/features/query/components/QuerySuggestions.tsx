/**
 * Query Suggestions Component
 * Shows sample queries to help users get started
 */

import { useQuery } from '@tanstack/react-query'
import { Lightbulb, TrendingUp, BarChart3, PieChart, Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import api from '@/lib/api'

const DEFAULT_SUGGESTIONS = [
  {
    text: 'What were the total sales by region last month?',
    icon: BarChart3,
    category: 'aggregation',
  },
  {
    text: 'Show me the top 10 products by revenue',
    icon: TrendingUp,
    category: 'ranking',
  },
  {
    text: 'Compare Q1 vs Q2 sales performance',
    icon: BarChart3,
    category: 'comparison',
  },
  {
    text: 'What is the average order value by customer segment?',
    icon: Users,
    category: 'aggregation',
  },
  {
    text: 'Show monthly revenue trend for the past year',
    icon: TrendingUp,
    category: 'trend',
  },
  {
    text: 'What percentage of sales come from each category?',
    icon: PieChart,
    category: 'distribution',
  },
]

interface QuerySuggestionsProps {
  onSelect: (query: string) => void
}

export function QuerySuggestions({ onSelect }: QuerySuggestionsProps) {
  // Try to fetch personalized suggestions based on available models
  const { data: personalSuggestions } = useQuery({
    queryKey: ['query-suggestions'],
    queryFn: async () => {
      try {
        const response = await api.get<string[]>('/api/v1/assistant/nl-to-sql/suggestions')
        return response.data
      } catch {
        return null
      }
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  })

  const suggestions = Array.isArray(personalSuggestions) && personalSuggestions.length > 0
    ? personalSuggestions.map((text, i) => ({
        text,
        icon: DEFAULT_SUGGESTIONS[i % DEFAULT_SUGGESTIONS.length].icon,
        category: 'suggested',
      }))
    : DEFAULT_SUGGESTIONS

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-yellow-500" />
          Try asking...
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 sm:grid-cols-2">
          {suggestions.map((suggestion, i) => {
            const Icon = suggestion.icon
            return (
              <Button
                key={i}
                variant="outline"
                className="h-auto py-3 px-4 text-left justify-start hover:bg-accent/50 transition-colors"
                onClick={() => onSelect(suggestion.text)}
              >
                <Icon className="h-4 w-4 mr-3 flex-shrink-0 text-muted-foreground" />
                <span className="text-sm leading-relaxed">{suggestion.text}</span>
              </Button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
