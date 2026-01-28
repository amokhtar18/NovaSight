/**
 * Data Table Widget
 */

import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  ColumnDef,
} from '@tanstack/react-table'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { TableColumn } from '@/types/dashboard'

interface DataTableProps {
  data: any[]
  columns: TableColumn[]
}

export function DataTable({ data, columns }: DataTableProps) {
  const tableColumns: ColumnDef<any>[] = columns.map((col) => ({
    accessorKey: col.field,
    header: col.label,
    cell: ({ getValue }) => {
      const value = getValue()
      
      if (col.type === 'number' && typeof value === 'number') {
        return value.toLocaleString()
      }
      
      if (col.type === 'date' && value) {
        return new Date(value as string).toLocaleDateString()
      }
      
      if (col.type === 'boolean') {
        return value ? '✓' : '✗'
      }
      
      return value?.toString() || '-'
    },
  }))
  
  const table = useReactTable({
    data,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
  })
  
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No data available
      </div>
    )
  }
  
  return (
    <ScrollArea className="h-full w-full">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext()
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </ScrollArea>
  )
}
