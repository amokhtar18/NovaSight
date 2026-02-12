/**
 * SQL Editor Component
 * Monaco-based SQL editor with syntax highlighting and schema-aware autocomplete
 */

import { useRef, useCallback, useEffect } from 'react'
import Editor, { OnMount, loader, Monaco } from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import { Play, Save, History, Loader2, Settings2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import type { SchemaInfo } from '../types'

// Configure Monaco to load from CDN
loader.config({
  paths: {
    vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs',
  },
})

interface SQLEditorProps {
  value: string
  onChange: (value: string) => void
  onExecute?: () => void
  onSave?: () => void
  isExecuting?: boolean
  executionTime?: number
  rowCount?: number
  className?: string
  readOnly?: boolean
  /** Schema data for autocomplete suggestions */
  schemas?: SchemaInfo[]
  /** Query result limit */
  queryLimit?: number
  /** Callback when query limit changes */
  onQueryLimitChange?: (limit: number) => void
}

export function SQLEditor({
  value,
  onChange,
  onExecute,
  onSave,
  isExecuting = false,
  executionTime,
  rowCount,
  className,
  readOnly = false,
  schemas = [],
  queryLimit = 200,
  onQueryLimitChange,
}: SQLEditorProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const editorRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const monacoRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const completionProviderRef = useRef<any>(null)

  // Build autocomplete suggestions from schemas
  const buildSuggestions = useCallback(() => {
    const tableNames: string[] = []
    const columnNames: Map<string, { name: string; type: string; table: string }[]> = new Map()
    const allColumns: { name: string; type: string; table: string }[] = []

    schemas.forEach((schema) => {
      schema.tables.forEach((table) => {
        const fullTableName = `${schema.name}.${table.name}`
        tableNames.push(fullTableName)
        tableNames.push(table.name) // Also add short name
        
        const tableColumns: { name: string; type: string; table: string }[] = []
        table.columns.forEach((column) => {
          const colInfo = { name: column.name, type: column.type, table: fullTableName }
          tableColumns.push(colInfo)
          allColumns.push(colInfo)
        })
        columnNames.set(fullTableName, tableColumns)
        columnNames.set(table.name, tableColumns)
      })
    })

    return { tableNames, columnNames, allColumns }
  }, [schemas])

  // Update completion provider when schemas change
  useEffect(() => {
    if (!monacoRef.current || !editorRef.current) return

    const monaco = monacoRef.current
    const { tableNames, columnNames, allColumns } = buildSuggestions()

    // Dispose previous provider
    if (completionProviderRef.current) {
      completionProviderRef.current.dispose()
    }

    // Register new completion provider
    completionProviderRef.current = monaco.languages.registerCompletionItemProvider('sql', {
      triggerCharacters: ['.', ' ', ','],
      provideCompletionItems: (
        model: { getWordUntilPosition: (pos: unknown) => { word: string; startColumn: number; endColumn: number }; getLineContent: (line: number) => string },
        position: { lineNumber: number; column: number }
      ) => {
        const word = model.getWordUntilPosition(position)
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        }

        const lineContent = model.getLineContent(position.lineNumber)
        const textBeforeCursor = lineContent.substring(0, position.column - 1)

        // Check if we're after a table name (for column suggestions)
        const tableMatch = textBeforeCursor.match(/(\w+(?:\.\w+)?)\s*\.\s*$/i)
        
        const suggestions: Array<{
          label: string
          kind: number
          insertText: string
          range: typeof range
          detail?: string
          documentation?: string
          sortText?: string
        }> = []

        if (tableMatch) {
          // Suggest columns for the specific table
          const tableName = tableMatch[1]
          const columns = columnNames.get(tableName) || []
          columns.forEach((col) => {
            suggestions.push({
              label: col.name,
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: col.name,
              range,
              detail: col.type,
              documentation: `Column: ${col.name}\nType: ${col.type}\nTable: ${col.table}`,
              sortText: '0' + col.name, // Prioritize columns
            })
          })
        } else {
          // Check context for better suggestions
          const isAfterFrom = /\bFROM\s+$/i.test(textBeforeCursor) || /\bJOIN\s+$/i.test(textBeforeCursor)
          const isAfterSelect = /\bSELECT\s+$/i.test(textBeforeCursor) || /,\s*$/i.test(textBeforeCursor)
          const isAfterWhere = /\bWHERE\s+$/i.test(textBeforeCursor) || /\bAND\s+$/i.test(textBeforeCursor) || /\bOR\s+$/i.test(textBeforeCursor)

          // Add table suggestions
          if (isAfterFrom || !isAfterSelect) {
            tableNames.forEach((tableName) => {
              suggestions.push({
                label: tableName,
                kind: monaco.languages.CompletionItemKind.Class,
                insertText: tableName,
                range,
                detail: 'Table',
                sortText: '1' + tableName,
              })
            })
          }

          // Add column suggestions
          if (isAfterSelect || isAfterWhere || suggestions.length === 0) {
            allColumns.forEach((col) => {
              suggestions.push({
                label: col.name,
                kind: monaco.languages.CompletionItemKind.Field,
                insertText: col.name,
                range,
                detail: `${col.type} (${col.table})`,
                sortText: '2' + col.name,
              })
            })
          }

          // SQL keywords
          const keywords = [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL',
            'ORDER', 'BY', 'ASC', 'DESC', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET',
            'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE',
            'TABLE', 'INDEX', 'DROP', 'ALTER', 'ADD', 'COLUMN', 'PRIMARY', 'KEY',
            'FOREIGN', 'REFERENCES', 'UNIQUE', 'DEFAULT', 'CHECK', 'CONSTRAINT',
            'UNION', 'ALL', 'DISTINCT', 'AS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'NULLIF', 'CAST',
            'WITH', 'RECURSIVE', 'EXISTS', 'ANY', 'SOME', 'OVER', 'PARTITION',
            'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LAG', 'LEAD', 'FIRST_VALUE', 'LAST_VALUE',
          ]

          keywords.forEach((keyword) => {
            if (keyword.toLowerCase().startsWith(word.word.toLowerCase())) {
              suggestions.push({
                label: keyword,
                kind: monaco.languages.CompletionItemKind.Keyword,
                insertText: keyword,
                range,
                sortText: '3' + keyword,
              })
            }
          })
        }

        return { suggestions }
      },
    })

    return () => {
      if (completionProviderRef.current) {
        completionProviderRef.current.dispose()
      }
    }
  }, [schemas, buildSuggestions])

  const handleEditorMount: OnMount = useCallback(
    (editorInstance: editor.IStandaloneCodeEditor, monacoInstance: Monaco) => {
      editorRef.current = editorInstance
      monacoRef.current = monacoInstance

      // Add keyboard shortcut for execute (Ctrl+Enter or Cmd+Enter)
      editorInstance.addCommand(monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.Enter, () => {
        onExecute?.()
      })

      // Add keyboard shortcut for save (Ctrl+S or Cmd+S)
      editorInstance.addCommand(monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.KeyS, () => {
        onSave?.()
      })

      // Focus editor
      editorInstance.focus()
    },
    [onExecute, onSave]
  )

  const handleEditorChange = useCallback(
    (newValue: string | undefined) => {
      onChange(newValue || '')
    },
    [onChange]
  )

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Toolbar */}
      <div className="flex items-center gap-2 p-2 border-b bg-muted/30">
        <Button
          size="sm"
          onClick={onExecute}
          disabled={isExecuting || !value.trim()}
          className="gap-1.5"
        >
          {isExecuting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          Run
          <kbd className="ml-1 text-xs opacity-60">Ctrl+Enter</kbd>
        </Button>

        {onSave && (
          <Button size="sm" variant="outline" onClick={onSave} className="gap-1.5">
            <Save className="h-4 w-4" />
            Save
          </Button>
        )}

        <Button size="sm" variant="ghost" className="gap-1.5">
          <History className="h-4 w-4" />
          History
        </Button>

        {/* Query Limit Settings */}
        {onQueryLimitChange && (
          <Popover>
            <PopoverTrigger asChild>
              <Button size="sm" variant="ghost" className="gap-1.5">
                <Settings2 className="h-4 w-4" />
                Limit: {queryLimit}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64" align="start">
              <div className="space-y-3">
                <div className="space-y-1">
                  <Label htmlFor="queryLimit" className="text-sm font-medium">
                    Query Result Limit
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Maximum number of rows to return
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    id="queryLimit"
                    type="number"
                    min={1}
                    max={10000}
                    value={queryLimit}
                    onChange={(e) => onQueryLimitChange(parseInt(e.target.value) || 200)}
                    className="h-8"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onQueryLimitChange(200)}
                  >
                    Reset
                  </Button>
                </div>
                <div className="flex gap-1">
                  {[100, 200, 500, 1000].map((limit) => (
                    <Button
                      key={limit}
                      size="sm"
                      variant={queryLimit === limit ? 'default' : 'outline'}
                      className="flex-1 h-7 text-xs"
                      onClick={() => onQueryLimitChange(limit)}
                    >
                      {limit}
                    </Button>
                  ))}
                </div>
              </div>
            </PopoverContent>
          </Popover>
        )}

        {/* Execution metadata */}
        {executionTime !== undefined && (
          <span className="ml-auto text-sm text-muted-foreground">
            {rowCount !== undefined && (
              <span className="mr-2">{rowCount.toLocaleString()} rows</span>
            )}
            <span>{executionTime}ms</span>
          </span>
        )}
      </div>

      {/* Editor */}
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          language="sql"
          theme="vs-dark"
          value={value}
          onChange={handleEditorChange}
          onMount={handleEditorMount}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            automaticLayout: true,
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            tabSize: 2,
            insertSpaces: true,
            readOnly,
            renderWhitespace: 'selection',
            folding: true,
            lineDecorationsWidth: 8,
            lineNumbersMinChars: 3,
            padding: { top: 8 },
            suggestOnTriggerCharacters: true,
            quickSuggestions: {
              other: true,
              comments: false,
              strings: true,
            },
            snippetSuggestions: 'inline',
            acceptSuggestionOnEnter: 'on',
            tabCompletion: 'on',
            wordBasedSuggestions: 'currentDocument',
            parameterHints: { enabled: true },
          }}
        />
      </div>
    </div>
  )
}
