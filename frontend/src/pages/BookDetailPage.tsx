/**
 * BookDetailPage — book detail + copies management at /librarian/books/:id.
 * Shows book metadata, inline edit form, physical copies list with CopyStatusBadge.
 * Add Copy form, Mark as Lost confirmation dialog, and Checkout modal for librarians.
 * Server is source of truth for availability — no client-side recalculation (T-03-02).
 *
 * Phase 3 additions (D-02, D-03, D-04, D-05):
 *   - "Check Out" button on available copies (librarian only)
 *   - Checkout modal with student search-as-you-type, selected student, approximate due date
 *   - Checkout mutation calls POST /api/librarian/loans/checkout
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { apiClient } from "@/lib/api";
import CopyStatusBadge from "../components/CopyStatusBadge";
import ConfirmDialog from "../components/ConfirmDialog";
import { checkoutCopy, searchStudents, type StudentUser } from "../api/loans";
import { useAuthStore } from "../store/auth";

interface Copy {
  id: number;
  book_id: number;
  barcode: string | null;
  condition: string;
  status: "available" | "on_loan" | "lost" | "withdrawn";
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
  const { user } = useAuthStore();

  // Edit form state
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editAuthor, setEditAuthor] = useState("");
  const [editIsbn, setEditIsbn] = useState("");
  const [editPublisher, setEditPublisher] = useState("");
  const [editPublishYear, setEditPublishYear] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [updateMessage, setUpdateMessage] = useState("");
  const [mutationError, setMutationError] = useState("");

  // Add copy form state
  const [showAddCopy, setShowAddCopy] = useState(false);
  const [copyBarcode, setCopyBarcode] = useState("");
  const [copyCondition, setCopyCondition] = useState("good");

  // Mark as lost dialog state
  const [lostDialogOpen, setLostDialogOpen] = useState(false);
  const [lostCopyId, setLostCopyId] = useState<number | null>(null);
  const [lostCopyLabel, setLostCopyLabel] = useState("");

  // Checkout modal state (D-02, D-03, D-04)
  const [checkoutCopyId, setCheckoutCopyId] = useState<number | null>(null);
  const [checkoutCopyLabel, setCheckoutCopyLabel] = useState("");
  const [studentQuery, setStudentQuery] = useState("");
  const [selectedStudent, setSelectedStudent] = useState<StudentUser | null>(null);
  const [checkoutError, setCheckoutError] = useState("");

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
      setMutationError("");
      setTimeout(() => setUpdateMessage(""), 3000);
    },
    onError: () => {
      setMutationError("Failed to save changes. Please try again.");
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
      setMutationError("");
    },
    onError: () => {
      setMutationError("Failed to add copy. Please try again.");
    },
  });

  const markLostMutation = useMutation({
    mutationFn: (copyId: number) =>
      apiClient.patch(`/copies/${copyId}/lost`).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book", id] });
      setLostDialogOpen(false);
      setLostCopyId(null);
      setMutationError("");
    },
    onError: () => {
      setMutationError("Failed to mark copy as lost. Please try again.");
    },
  });

  // Student search for checkout modal (D-03) — enabled when query >= 2 chars
  const { data: studentSearchResults } = useQuery({
    queryKey: ["student-search", studentQuery],
    queryFn: () => searchStudents(studentQuery),
    enabled: studentQuery.length >= 2,
  });

  // Checkout mutation (D-05)
  const checkoutMutation = useMutation({
    mutationFn: ({
      copyId,
      userId,
    }: {
      copyId: number;
      userId: number;
    }) => checkoutCopy(copyId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["book", id] });
      queryClient.invalidateQueries({ queryKey: ["librarian-loans"] });
      setCheckoutCopyId(null);
      setStudentQuery("");
      setSelectedStudent(null);
      setCheckoutError("");
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError?.response?.status === 409) {
        setCheckoutError("This copy is no longer available.");
      } else if (axiosError?.response?.status === 400) {
        setCheckoutError("Selected user is not a student account.");
      } else {
        setCheckoutError("Checkout failed. Please try again.");
      }
    },
  });

  // Approximate due date: today + 14 days (server computes actual from library_settings — D-04)
  const approxDueDate = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toLocaleDateString(
    "en-US",
    { year: "numeric", month: "short", day: "numeric" }
  );

  function openCheckoutModal(copy: Copy) {
    setCheckoutCopyId(copy.id);
    setCheckoutCopyLabel(copy.barcode ?? `Copy #${copy.id}`);
    setStudentQuery("");
    setSelectedStudent(null);
    setCheckoutError("");
  }

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
    // Validate required fields before submitting (WR-02)
    if (!editTitle.trim()) {
      setMutationError("Title is required.");
      return;
    }
    if (!editAuthor.trim()) {
      setMutationError("Author is required.");
      return;
    }
    setMutationError("");
    const payload: BookUpdatePayload = {
      title: editTitle.trim(),
      author: editAuthor.trim(),
      isbn: editIsbn.trim() || null,
      publisher: editPublisher.trim() || null,
      publish_year: (() => { const y = parseInt(editPublishYear, 10); return editPublishYear.trim() && !isNaN(y) ? y : null; })(),
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

  // Show all copies including lost for audit purposes. The filter was always
  // true (status is always defined) so we use the full array directly (WR-04).
  const allCopies = book.copies;

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

      {/* Mutation error message */}
      {mutationError && (
        <p className="text-red-600 text-sm mb-3">{mutationError}</p>
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

      {allCopies.length === 0 ? (
        <p className="text-sm text-gray-500">
          No copies added yet. Add a physical copy to make this book available.
        </p>
      ) : (
        <div className="flex flex-col gap-2 mb-4">
          {allCopies.map((copy) => (
            <div
              key={copy.id}
              className="flex items-center gap-3 py-2 border-b last:border-b-0"
            >
              <span className="text-sm text-gray-700">
                {copy.barcode ?? `Copy #${copy.id}`}
              </span>
              <CopyStatusBadge status={copy.status} />
              {/* Check Out button — librarian only, available copies only (D-02, D-05) */}
              {user?.role === "librarian" && copy.status === "available" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-blue-600 border-blue-300 hover:bg-blue-50"
                  onClick={() => openCheckoutModal(copy)}
                >
                  Check Out
                </Button>
              )}
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

      {/* Checkout modal — student search + confirm checkout (D-02, D-03, D-04, D-05) */}
      <Dialog
        open={checkoutCopyId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setCheckoutCopyId(null);
            setStudentQuery("");
            setSelectedStudent(null);
            setCheckoutError("");
          }
        }}
      >
        <DialogContent showCloseButton>
          <DialogHeader>
            <DialogTitle>Check out {checkoutCopyLabel}</DialogTitle>
          </DialogHeader>

          {/* Student search */}
          <div className="flex flex-col gap-1 relative">
            <Label htmlFor="student-search">Student</Label>
            <Input
              id="student-search"
              placeholder="Type student name or email..."
              value={studentQuery}
              onChange={(e) => {
                setStudentQuery(e.target.value);
                setSelectedStudent(null);
              }}
              autoComplete="off"
            />
            {/* Dropdown results */}
            {studentQuery.length >= 2 &&
              !selectedStudent &&
              studentSearchResults &&
              studentSearchResults.length > 0 && (
                <ul className="absolute top-full left-0 right-0 z-50 mt-1 rounded-md border bg-white shadow-md max-h-48 overflow-auto text-sm">
                  {studentSearchResults.map((student) => (
                    <li
                      key={student.id}
                      className="px-3 py-2 cursor-pointer hover:bg-gray-100"
                      onClick={() => {
                        setSelectedStudent(student);
                        setStudentQuery(student.email);
                      }}
                    >
                      <div className="font-medium">{student.full_name}</div>
                      <div className="text-gray-500 text-xs">{student.email}</div>
                    </li>
                  ))}
                </ul>
              )}
          </div>

          {/* Selected student display */}
          {selectedStudent && (
            <div className="rounded-md bg-blue-50 px-3 py-2 text-sm">
              <span className="font-medium">{selectedStudent.full_name}</span>
              <span className="text-gray-500 ml-2">{selectedStudent.email}</span>
            </div>
          )}

          {/* Approximate due date (read-only — D-04) */}
          <div className="text-sm text-gray-600">
            <span className="font-medium">Due:</span> {approxDueDate}
            <span className="text-gray-400 text-xs ml-2">(approximate — server uses library settings)</span>
          </div>

          {/* Checkout error */}
          {checkoutError && (
            <p className="text-sm text-red-600">{checkoutError}</p>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setCheckoutCopyId(null);
                setStudentQuery("");
                setSelectedStudent(null);
                setCheckoutError("");
              }}
              disabled={checkoutMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              className="bg-blue-600 text-white hover:bg-blue-700"
              disabled={!selectedStudent || checkoutMutation.isPending}
              onClick={() => {
                if (checkoutCopyId !== null && selectedStudent) {
                  checkoutMutation.mutate({
                    copyId: checkoutCopyId,
                    userId: selectedStudent.id,
                  });
                }
              }}
            >
              {checkoutMutation.isPending ? "Checking out..." : "Confirm Checkout"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
