/**
 * LibrarianFinesPage — fines management dashboard at /librarian/fines.
 * Shows all fines in a table with Pay and Waive actions per row.
 * Pay opens a ConfirmDialog; Waive opens a Dialog with a reason textarea.
 * Both actions invalidate the ["librarian-fines"] query on success.
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import ConfirmDialog from "../components/ConfirmDialog";
import { getLibrarianFines, payFine, waiveFine, type FineItem } from "../api/fines";

export default function LibrarianFinesPage() {
  const queryClient = useQueryClient();

  // Pay confirmation dialog state
  const [payDialogOpen, setPayDialogOpen] = useState(false);
  const [payTargetId, setPayTargetId] = useState<number | null>(null);
  const [payTargetLabel, setPayTargetLabel] = useState("");

  // Waive dialog state
  const [waiveDialogOpen, setWaiveDialogOpen] = useState(false);
  const [waiveTargetId, setWaiveTargetId] = useState<number | null>(null);
  const [waiveReason, setWaiveReason] = useState("");

  // Fetch fines
  const { data, isLoading } = useQuery({
    queryKey: ["librarian-fines"],
    queryFn: () => getLibrarianFines(),
  });

  // Pay mutation
  const payMutation = useMutation({
    mutationFn: (fineId: number) => payFine(fineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["librarian-fines"] });
      setPayDialogOpen(false);
      setPayTargetId(null);
    },
  });

  // Waive mutation
  const waiveMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      waiveFine(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["librarian-fines"] });
      setWaiveDialogOpen(false);
      setWaiveTargetId(null);
      setWaiveReason("");
    },
  });

  function openPayDialog(fine: FineItem) {
    setPayTargetId(fine.id);
    setPayTargetLabel(`${fine.loan.book.title} — $${Number(fine.amount).toFixed(2)}`);
    setPayDialogOpen(true);
  }

  function openWaiveDialog(fine: FineItem) {
    setWaiveTargetId(fine.id);
    setWaiveReason("");
    setWaiveDialogOpen(true);
  }

  // TanStack Table v8 column definitions
  const columns: ColumnDef<FineItem>[] = [
    {
      id: "borrower",
      header: "Borrower",
      cell: ({ row }) => (
        <div>
          <div className="text-sm font-medium text-gray-900">
            {row.original.loan.borrower.full_name ?? ""}
          </div>
          <div className="text-xs text-gray-500">
            {row.original.loan.borrower.email}
          </div>
        </div>
      ),
    },
    {
      id: "book",
      header: "Book",
      cell: ({ row }) => (
        <span className="text-sm text-gray-800">
          {row.original.loan.book.title}
        </span>
      ),
    },
    {
      id: "amount",
      header: "Amount",
      cell: ({ row }) => (
        <span className="text-sm font-medium text-gray-900">
          ${Number(row.original.amount).toFixed(2)}
        </span>
      ),
    },
    {
      id: "days_overdue",
      header: "Days Overdue",
      cell: ({ row }) => (
        <span className="text-sm text-gray-700">{row.original.days_overdue}</span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: ({ row }) => {
        const s = row.original.status;
        if (s === "paid") {
          return (
            <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
              Paid
            </span>
          );
        }
        if (s === "waived") {
          return (
            <span className="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-700">
              Waived
            </span>
          );
        }
        return (
          <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
            Unpaid
          </span>
        );
      },
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const isSettled = row.original.status !== "unpaid";
        return (
          <div className="flex gap-2">
            <Button
              variant="default"
              size="sm"
              onClick={() => openPayDialog(row.original)}
              disabled={isSettled || payMutation.isPending}
            >
              Pay
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openWaiveDialog(row.original)}
              disabled={isSettled || waiveMutation.isPending}
            >
              Waive
            </Button>
          </div>
        );
      },
    },
  ];

  const fines = data?.items ?? [];

  const table = useReactTable({
    data: fines,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-semibold text-gray-900 mb-6">Fines</h1>

      {/* Fines table */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 rounded bg-gray-100 animate-pulse" />
          ))}
        </div>
      ) : fines.length === 0 ? (
        <p className="text-gray-500 text-sm py-8 text-center">
          No fines recorded yet.
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

      {/* Pay confirmation dialog */}
      <ConfirmDialog
        open={payDialogOpen}
        onOpenChange={setPayDialogOpen}
        title="Mark Fine as Paid"
        description={`Record payment for this fine?\n${payTargetLabel}`}
        confirmLabel="Mark Paid"
        cancelLabel="Cancel"
        onConfirm={() => {
          if (payTargetId !== null) {
            payMutation.mutate(payTargetId);
          }
        }}
        isLoading={payMutation.isPending}
      />

      {/* Waive reason dialog */}
      <Dialog open={waiveDialogOpen} onOpenChange={(open) => {
        setWaiveDialogOpen(open);
        if (!open) setWaiveReason("");
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Waive Fine</DialogTitle>
            <DialogDescription>
              Provide a reason for waiving this fine. The reason will be stored
              with the fine record.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-2">
            <textarea
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
              placeholder="Enter waiver reason (required)"
              value={waiveReason}
              onChange={(e) => setWaiveReason(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setWaiveDialogOpen(false);
                setWaiveReason("");
              }}
              disabled={waiveMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="default"
              onClick={() => {
                if (waiveTargetId !== null && waiveReason.trim()) {
                  waiveMutation.mutate({ id: waiveTargetId, reason: waiveReason });
                }
              }}
              disabled={
                !waiveReason.trim() || waiveMutation.isPending
              }
            >
              {waiveMutation.isPending ? "Saving..." : "Waive Fine"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
