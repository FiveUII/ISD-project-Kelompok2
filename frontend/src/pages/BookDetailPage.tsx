/**
 * BookDetailPage — book detail + copies management at /librarian/books/:id.
 * Shows book metadata, inline edit form, physical copies list with CopyStatusBadge.
 * Add Copy form and Mark as Lost confirmation dialog.
 * Server is source of truth for availability — no client-side recalculation (T-03-02).
 */
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/lib/api";
import CopyStatusBadge from "../components/CopyStatusBadge";
import ConfirmDialog from "../components/ConfirmDialog";

interface Copy {
  id: number;
  book_id: number;
  barcode: string | null;
  condition: string;
  status: "available" | "on_loan" | "lost";
  created_at: string;
}

interface BookDetail {
  id: number;
  isbn: string | null;
  title: string;
  author: string;
  publisher: string | null;
  publish_year: number | null;
  description: string | null;
  cover_url: string | null;
  available_count: number;
  total_count: number;
  copies: Copy[];
}

interface BookUpdatePayload {
  isbn?: string | null;
  title?: string;
  author?: string;
  publisher?: string | null;
  publish_year?: number | null;
  description?: string | null;
  cover_url?: string | null;
}

export default function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  // Edit form state
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editAuthor, setEditAuthor] = useState("");
  const [editIsbn, setEditIsbn] = useState("");
  const [editPublisher, setEditPublisher] = useState("");
  const [editPublishYear, setEditPublishYear] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [updateMessage, setUpdateMessage] = useState("");

  // Add copy form state
  const [showAddCopy, setShowAddCopy] = useState(false);
  const [copyBarcode, setCopyBarcode] = useState("");
  const [copyCondition, setCopyCondition] = useState("good");

  // Mark as lost dialog state
  const [lostDialogOpen, setLostDialogOpen] = useState(false);
  const [lostCopyId, setLostCopyId] = useState<number | null>(null);
  const [lostCopyLabel, setLostCopyLabel] = useState("");

  const { data: book, isLoading } = useQuery<BookDetail>({
    queryKey: ["book", id],
    queryFn: () => apiClient.get<BookDetail>(`/books/${id}`).then((r) => r.data),
    enabled: Boolean(id),
  });

  const updateMutation = useMutation<BookDetail, unknown, BookUpdatePayload>({
    mutationFn: (data) =>
      apiClient.put<BookDetail>(`/books/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book", id] });
      setIsEditing(false);
      setUpdateMessage("Book updated.");
      setTimeout(() => setUpdateMessage(""), 3000);
    },
  });

  const addCopyMutation = useMutation({
    mutationFn: (data: { barcode?: string; condition: string }) =>
      apiClient.post(`/books/${id}/copies`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book", id] });
      setShowAddCopy(false);
      setCopyBarcode("");
      setCopyCondition("good");
    },
  });

  const markLostMutation = useMutation({
    mutationFn: (copyId: number) =>
      apiClient.patch(`/copies/${copyId}/lost`).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book", id] });
      setLostDialogOpen(false);
      setLostCopyId(null);
    },
  });

  function startEditing(book: BookDetail) {
    setEditTitle(book.title);
    setEditAuthor(book.author);
    setEditIsbn(book.isbn ?? "");
    setEditPublisher(book.publisher ?? "");
    setEditPublishYear(book.publish_year ? String(book.publish_year) : "");
    setEditDescription(book.description ?? "");
    setIsEditing(true);
    setUpdateMessage("");
  }

  function handleSaveChanges(e: React.FormEvent) {
    e.preventDefault();
    const payload: BookUpdatePayload = {
      title: editTitle.trim() || undefined,
      author: editAuthor.trim() || undefined,
      isbn: editIsbn.trim() || null,
      publisher: editPublisher.trim() || null,
      publish_year: editPublishYear ? parseInt(editPublishYear, 10) : null,
      description: editDescription.trim() || null,
    };
    updateMutation.mutate(payload);
  }

  function handleAddCopy(e: React.FormEvent) {
    e.preventDefault();
    const payload: { barcode?: string; condition: string } = {
      condition: copyCondition,
    };
    if (copyBarcode.trim()) payload.barcode = copyBarcode.trim();
    addCopyMutation.mutate(payload);
  }

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <p className="text-gray-500">Book not found.</p>
      </div>
    );
  }

  const activeCopies = book.copies.filter((c) => c.status !== undefined);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Book header */}
      <div className="flex justify-between items-start mb-2">
        <h1 className="text-3xl font-semibold text-gray-900">{book.title}</h1>
        {!isEditing && (
          <Button variant="outline" onClick={() => startEditing(book)}>
            Edit Book
          </Button>
        )}
      </div>

      {/* Update message */}
      {updateMessage && (
        <p className="text-green-600 text-sm mb-3">{updateMessage}</p>
      )}

      {/* Inline edit form */}
      {isEditing ? (
        <form onSubmit={handleSaveChanges} className="flex flex-col gap-4 mb-6">
          <div className="flex flex-col gap-1">
            <Label htmlFor="edit-title">Title</Label>
            <Input
              id="edit-title"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="edit-author">Author</Label>
            <Input
              id="edit-author"
              value={editAuthor}
              onChange={(e) => setEditAuthor(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="edit-isbn">ISBN</Label>
            <Input
              id="edit-isbn"
              value={editIsbn}
              onChange={(e) => setEditIsbn(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="edit-publisher">Publisher</Label>
            <Input
              id="edit-publisher"
              value={editPublisher}
              onChange={(e) => setEditPublisher(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="edit-publish-year">Publish Year</Label>
            <Input
              id="edit-publish-year"
              type="number"
              value={editPublishYear}
              onChange={(e) => setEditPublishYear(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="edit-description">Description</Label>
            <textarea
              id="edit-description"
              className="w-full border rounded px-3 py-2 text-sm"
              rows={4}
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
            />
          </div>
          <div className="flex gap-3">
            <Button
              type="submit"
              className="bg-blue-600 text-white hover:bg-blue-700"
              disabled={updateMutation.isPending}
            >
              Save Changes
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsEditing(false)}
            >
              Discard Changes
            </Button>
          </div>
        </form>
      ) : (
        /* Book metadata */
        <div className="flex flex-col gap-2 mb-4">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Author:</span> {book.author}
          </p>
          {book.isbn && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">ISBN:</span> {book.isbn}
            </p>
          )}
          {book.publisher && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Publisher:</span> {book.publisher}
            </p>
          )}
          {book.publish_year && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Published:</span> {book.publish_year}
            </p>
          )}
          {book.description && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Description:</span> {book.description}
            </p>
          )}
        </div>
      )}

      <Separator />

      {/* Copies section */}
      <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">
        Physical Copies
      </h2>

      {activeCopies.length === 0 ? (
        <p className="text-sm text-gray-500">
          No copies added yet. Add a physical copy to make this book available.
        </p>
      ) : (
        <div className="flex flex-col gap-2 mb-4">
          {activeCopies.map((copy) => (
            <div
              key={copy.id}
              className="flex items-center gap-3 py-2 border-b last:border-b-0"
            >
              <span className="text-sm text-gray-700">
                {copy.barcode ?? `Copy #${copy.id}`}
              </span>
              <CopyStatusBadge status={copy.status} />
              {copy.status !== "lost" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setLostCopyId(copy.id);
                    setLostCopyLabel(copy.barcode ?? String(copy.id));
                    setLostDialogOpen(true);
                  }}
                >
                  Mark as Lost
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add Copy */}
      {!showAddCopy ? (
        <Button
          className="bg-blue-600 text-white hover:bg-blue-700"
          onClick={() => setShowAddCopy(true)}
        >
          Add Copy
        </Button>
      ) : (
        <form onSubmit={handleAddCopy} className="flex flex-col gap-3 mt-3 max-w-sm">
          <div className="flex flex-col gap-1">
            <Label htmlFor="copy-barcode">Barcode (optional)</Label>
            <Input
              id="copy-barcode"
              value={copyBarcode}
              onChange={(e) => setCopyBarcode(e.target.value)}
              placeholder="e.g. BC-0001"
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="copy-condition">Condition</Label>
            <select
              id="copy-condition"
              className="w-full border rounded px-3 py-2 text-sm"
              value={copyCondition}
              onChange={(e) => setCopyCondition(e.target.value)}
            >
              <option value="new">New</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
              <option value="poor">Poor</option>
            </select>
          </div>
          <div className="flex gap-3">
            <Button
              type="submit"
              className="bg-blue-600 text-white hover:bg-blue-700"
              disabled={addCopyMutation.isPending}
            >
              Add Copy
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowAddCopy(false)}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}

      {/* Mark as Lost confirmation dialog */}
      <ConfirmDialog
        open={lostDialogOpen}
        onOpenChange={setLostDialogOpen}
        title="Mark copy as lost"
        description={`Copy ${lostCopyLabel} will be marked as lost and removed from available inventory.`}
        confirmLabel="Mark as Lost"
        cancelLabel="Keep Copy"
        onConfirm={() => {
          if (lostCopyId !== null) {
            markLostMutation.mutate(lostCopyId);
          }
        }}
        isLoading={markLostMutation.isPending}
      />
    </div>
  );
}
