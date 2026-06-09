/**
 * LibrarianBooksPage — librarian book management page at /librarian/books.
 * Displays a sortable DataTable with search and Add Book button.
 * Soft-delete via ConfirmDialog (no browser confirm()).
 */
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import BookDataTable from "../components/BookDataTable";
import ConfirmDialog from "../components/ConfirmDialog";
import type { BookRow } from "../components/BookDataTable";

interface BookListResponse {
  items: BookRow[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export default function LibrarianBooksPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const page = Number(searchParams.get("page") ?? "1");

  const [inputValue, setInputValue] = useState(q);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const queryClient = useQueryClient();

  const { data } = useQuery<BookListResponse>({
    queryKey: ["librarian-books", { q, page, page_size: 20 }],
    queryFn: () =>
      apiClient
        .get("/books", { params: { q: q || undefined, page, page_size: 20 } })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/books/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["librarian-books"] });
      setDeleteDialogOpen(false);
      setDeleteTargetId(null);
      setErrorMessage("");
    },
    onError: () => {
      setErrorMessage("Failed to delete book. Please try again.");
    },
  });

  function handleSearch() {
    setSearchParams({ q: inputValue, page: "1" });
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header row */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-semibold text-gray-900">Manage Books</h1>
        <Button
          onClick={() => navigate("/librarian/books/new")}
          className="bg-blue-600 text-white hover:bg-blue-700"
        >
          Add Book
        </Button>
      </div>

      {/* Error message */}
      {errorMessage && (
        <p className="text-red-600 text-sm mb-4">{errorMessage}</p>
      )}

      {/* Search */}
      <div className="mb-4 max-w-md">
        <div className="flex gap-2">
          <Input
            placeholder="Search by title, author, or ISBN..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch();
            }}
          />
          <Button
            onClick={handleSearch}
            className="bg-blue-600 text-white hover:bg-blue-700"
          >
            Search
          </Button>
        </div>
      </div>

      {/* DataTable */}
      <BookDataTable
        books={data?.items ?? []}
        onEdit={(id) => navigate(`/librarian/books/${id}`)}
        onDelete={(id) => {
          setDeleteTargetId(id);
          setDeleteDialogOpen(true);
        }}
      />

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete book"
        description="This will remove the book from the catalog. Loan history is preserved. This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Keep Book"
        onConfirm={() => {
          if (deleteTargetId !== null) {
            deleteMutation.mutate(deleteTargetId);
          }
        }}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
