/**
 * BookDataTable — sortable TanStack Table for the librarian book management page.
 * Columns: Title, Author, ISBN, Available, Copies, Actions (Edit + Delete).
 * Default sort: Title ascending.
 * Uses shadcn Table components and AvailabilityBadge.
 */
import { useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import AvailabilityBadge from "./AvailabilityBadge";

export interface BookRow {
  id: number;
  isbn: string | null;
  title: string;
  author: string;
  available_count: number;
  total_count: number;
}

interface BookDataTableProps {
  books: BookRow[];
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}

export default function BookDataTable({
  books,
  onEdit,
  onDelete,
}: BookDataTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "title", desc: false },
  ]);

  const columns: ColumnDef<BookRow>[] = [
    {
      accessorKey: "title",
      header: ({ column }) => (
        <button
          className="flex items-center gap-1 font-medium hover:text-foreground"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Title
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground" />
          )}
        </button>
      ),
    },
    {
      accessorKey: "author",
      header: ({ column }) => (
        <button
          className="flex items-center gap-1 font-medium hover:text-foreground"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Author
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground" />
          )}
        </button>
      ),
    },
    {
      accessorKey: "isbn",
      header: ({ column }) => (
        <button
          className="flex items-center gap-1 font-medium hover:text-foreground"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          ISBN
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground" />
          )}
        </button>
      ),
      cell: ({ row }) => row.original.isbn ?? "—",
    },
    {
      accessorKey: "available_count",
      header: ({ column }) => (
        <button
          className="flex items-center gap-1 font-medium hover:text-foreground"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Available
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground" />
          )}
        </button>
      ),
      cell: ({ row }) => (
        <AvailabilityBadge count={row.original.available_count} />
      ),
    },
    {
      accessorKey: "total_count",
      header: ({ column }) => (
        <button
          className="flex items-center gap-1 font-medium hover:text-foreground"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Copies
          {column.getIsSorted() === "asc" ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : column.getIsSorted() === "desc" ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground" />
          )}
        </button>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      cell: ({ row }) => (
        <div className="flex gap-3">
          <button
            className="text-blue-600 text-sm font-semibold hover:underline"
            aria-label={`Edit ${row.original.title}`}
            onClick={() => onEdit(row.original.id)}
          >
            Edit
          </button>
          <button
            className="text-red-600 text-sm font-semibold hover:underline"
            aria-label={`Delete ${row.original.title}`}
            onClick={() => onDelete(row.original.id)}
          >
            Delete
          </button>
        </div>
      ),
    },
  ];

  const table = useReactTable({
    data: books,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {header.isPlaceholder
                  ? null
                  : flexRender(header.column.columnDef.header, header.getContext())}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={6} className="text-center py-12 text-gray-500">
              No books in the catalog yet
              <br />
              <span className="text-xs">Add your first book to get started.</span>
            </TableCell>
          </TableRow>
        ) : (
          table.getRowModel().rows.map((row) => (
            <TableRow key={row.id} className="hover:bg-gray-50">
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
