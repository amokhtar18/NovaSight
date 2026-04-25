import { Database, FileText, Table2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { DATABASE_TYPES, type DatabaseType, type SourceCategory } from '@/types/datasource'
import { Badge } from '@/components/ui/badge'

interface DataSourceTypeSelectorProps {
  selected: DatabaseType | null
  onSelect: (type: DatabaseType) => void
}

const CATEGORY_LABELS: Record<SourceCategory, string> = {
  database: 'Databases',
  file: 'File Sources',
}

function TypeIcon({ icon }: { icon: string }) {
  if (icon === 'file-text') return <FileText className="h-8 w-8" />
  if (icon === 'table-2') return <Table2 className="h-8 w-8" />
  return <Database className="h-8 w-8" />
}

export function DataSourceTypeSelector({ selected, onSelect }: DataSourceTypeSelectorProps) {
  const byCategory = Object.values(DATABASE_TYPES).reduce<Record<SourceCategory, typeof DATABASE_TYPES[DatabaseType][]>>(
    (acc, info) => {
      acc[info.category].push(info)
      return acc
    },
    { database: [], file: [] }
  )

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-2">Select Data Source Type</h3>
        <p className="text-sm text-muted-foreground">
          Choose a database to connect to, or upload a file
        </p>
      </div>

      {(['database', 'file'] as SourceCategory[]).map((cat) => (
        <div key={cat}>
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            {CATEGORY_LABELS[cat]}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {byCategory[cat].map((dbType) => (
              <Card
                key={dbType.type}
                className={cn(
                  "p-6 cursor-pointer transition-all hover:shadow-md",
                  selected === dbType.type
                    ? "border-primary ring-2 ring-primary ring-offset-2"
                    : "hover:border-primary/50"
                )}
                onClick={() => onSelect(dbType.type)}
              >
                <div className="flex flex-col items-center text-center space-y-3">
                  <div
                    className={cn(
                      "p-3 rounded-lg",
                      selected === dbType.type
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    )}
                  >
                    <TypeIcon icon={dbType.icon} />
                  </div>
                  <div className="space-y-1">
                    <h4 className="font-semibold">{dbType.name}</h4>
                    <p className="text-xs text-muted-foreground">
                      {dbType.description}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1 justify-center">
                    {dbType.supportsSSL && (
                      <Badge variant="secondary" className="text-xs">SSL</Badge>
                    )}
                    {dbType.supportsSchemas && (
                      <Badge variant="secondary" className="text-xs">Schemas</Badge>
                    )}
                    {dbType.requiresUpload && (
                      <Badge variant="outline" className="text-xs">Upload</Badge>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
