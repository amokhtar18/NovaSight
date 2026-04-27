import { Database } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { DATABASE_TYPES, type DatabaseType } from '@/types/datasource'
import { Badge } from '@/components/ui/badge'

interface DataSourceTypeSelectorProps {
  selected: DatabaseType | null
  onSelect: (type: DatabaseType) => void
}

export function DataSourceTypeSelector({ selected, onSelect }: DataSourceTypeSelectorProps) {
  const types = Object.values(DATABASE_TYPES)

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-2">Select Database Type</h3>
        <p className="text-sm text-muted-foreground">
          Choose a database to connect to. To ingest a CSV / Excel / Parquet file, use the
          Pipeline Builder instead.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {types.map((dbType) => (
          <Card
            key={dbType.type}
            className={cn(
              'p-6 cursor-pointer transition-all hover:shadow-md',
              selected === dbType.type
                ? 'border-primary ring-2 ring-primary ring-offset-2'
                : 'hover:border-primary/50'
            )}
            onClick={() => onSelect(dbType.type)}
          >
            <div className="flex flex-col items-center text-center space-y-3">
              <div
                className={cn(
                  'p-3 rounded-lg',
                  selected === dbType.type
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                )}
              >
                <Database className="h-8 w-8" />
              </div>
              <div className="space-y-1">
                <h4 className="font-semibold">{dbType.name}</h4>
                <p className="text-xs text-muted-foreground">{dbType.description}</p>
              </div>
              <div className="flex flex-wrap gap-1 justify-center">
                {dbType.supportsSSL && (
                  <Badge variant="secondary" className="text-xs">SSL</Badge>
                )}
                {dbType.supportsSchemas && (
                  <Badge variant="secondary" className="text-xs">Schemas</Badge>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
