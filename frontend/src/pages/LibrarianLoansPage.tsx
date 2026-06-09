/**
 * LibrarianLoansPage — loans dashboard at /librarian/loans.
 * Two tabs: Active Loans and Overdue Loans, each backed by the loans API.
 * Active tab: full loan table with Return action wrapped in ConfirmDialog.
 * Overdue tab: same table with overdue=true filter.
 *
 * TanStack Table v8 for column rendering.
 * TanStack Query for data fetching and mutation invalidation.
 */
import { useState } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from "@tanstack/react-table";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import ConfirmDialog from "../components/ConfirmDialog";
import { getLibrarianLoans, returnLoan, type LoanItem } from "../api/loans";

type ActiveTab = "active" | "overdue";

export default function LibrarianLoansPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<ActiveTab>("active");

  // Return confirmation dialog state
  const [returnDialogOpen, setReturnDialogOpen] = useState(false);
  const [returnTargetId, setReturnTargetId] = useState<number | null>(null);
  const [returnTargetLabel, setReturnTargetLabel] = useState("");

  // Fetch loans based on active tab
  const { data, isLoading } = useQuery({
    queryKey: ["librarian-loans", activeTab],
    queryFn: () => getLibrarianLoans(activeTab === "overdue"),
  });

  // Return mutation
  const returnMutation = useMutation({
    mutationFn: (loanId: number) => returnLoan(loanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["librarian-loans"] });
      setReturnDialogOpen(false);
      setReturnTargetId(null);
    },
  });

  function openReturnDialog(loan: LoanItem) {
    setReturnTargetId(loan.id);
    setReturnTargetLabel(
      `${loan.book.title} — ${loan.copy.barcode ?? `Copy #${loan.copy.id}`}`
    );
    setReturnDialogOpen(true);
  }

  // TanStack Table v8 column definitions
  const columns: ColumnDef<LoanItem>[] = [
    {
      id: "student",
      header: "Student",
      cell: ({ row }) => (
        <div>
          <div className="text-sm font-medium text-gray-900">
            {row.original.borrower.full_name ?? ""}
          </div>
          <div className="text-xs text-gray-500">{row.original.borrower.email}</div>
        </div>
      ),
    },
    {
      id: "book",
      header: "Book",
      cell: ({ row }) => (
        <span className="text-sm text-gray-800">{row.original.book.title}</span>
      ),
    },
    {
      id: "copy",
      header: "Copy",
      cell: ({ row }) => (
        <span className="text-sm text-gray-700">
          {row.original.copy.barcode ?? `Copy #${row.original.copy.id}`}
        </span>
      ),
    },
    {
      id: "due_date",
      header: "Due Date",
      cell: ({ row }) => (
        <span className="text-sm text-gray-700">
          {new Date(row.original.due_date).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: ({ row }) =>
        row.original.is_overdue ? (
          <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
            Overdue
          </span>
        ) : (
          <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
            Active
          </span>
        ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <Button
          variant="destructive"
          size="sm"
          onClick={() => openReturnDialog(row.original)}
          disabled={returnMutation.isPending}
        >
          Return
        </Button>
      ),
    },
  ];

  const loans = data?.items ?? [];

  const table = useReactTable({
    data: loans,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-semibold text-gray-900 mb-6">Loans</h1>

      {/* Tab buttons */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        <button
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === "active"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setActiveTab("active")}
        >
          Active Loans
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === "overdue"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setActiveTab("overdue")}
        >
          Overdue Loans
        </button>
      </div>

      {/* Loans table */}
      {isLoading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : loans.length === 0 ? (
        <p className="text-gray-500 text-sm py-8 text-center">
          {activeTab === "active" ? "No active loans." : "No overdue loans."}
        </p>
      ) : (
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
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
              <TableRow key={row.id} className="hover:bg-gray-50">
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Return confirmation dialog */}
      <ConfirmDialog
        open={returnDialogOpen}
        onOpenChange={setReturnDialogOpen}
        title="Return Book"
        description={`Mark this loan as returned? The copy will become available.\n${returnTargetLabel}`}
        confirmLabel="Return"
        cancelLabel="Cancel"
        onConfirm={() => {
          if (returnTargetId !== null) {
            returnMutation.mutate(returnTargetId);
          }
        }}
        isLoading={returnMutation.isPending}
      />
    </div>
  );
}
