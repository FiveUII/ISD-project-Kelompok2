/**
 * AddBookPage — librarian form at /librarian/books/new.
 * ISBN fetch auto-populates title, author, description, cover_url (NOT publisher/year per D-03).
 * Validation: title and author required.
 * On save: POST /api/books → redirect to /librarian/books/{id}
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import ISBNFetchButton, { type ISBNFetchResult } from "../components/ISBNFetchButton";

interface BookCreatePayload {
  isbn?: string;
  title: string;
  author: string;
  description?: string;
  publisher?: string;
  publish_year?: number;
  cover_url?: string;
}

interface BookResponse {
  id: number;
  title: string;
  author: string;
}

export default function AddBookPage() {
  const navigate = useNavigate();

  const [isbn, setIsbn] = useState("");
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [description, setDescription] = useState("");
  const [publisher, setPublisher] = useState("");
  const [publishYear, setPublishYear] = useState("");
  const [coverUrl, setCoverUrl] = useState("");

  const [titleError, setTitleError] = useState("");
  const [authorError, setAuthorError] = useState("");

  const createMutation = useMutation<BookResponse, unknown, BookCreatePayload>({
    mutationFn: (data) => apiClient.post<BookResponse>("/books", data).then((r) => r.data),
    onSuccess: (book) => {
      navigate(`/librarian/books/${book.id}`);
    },
  });

  function handleFetchResult(result: ISBNFetchResult) {
    if (result.found) {
      setTitle(result.title ?? "");
      setAuthor(result.author ?? "");
      setDescription(result.description ?? "");
      setCoverUrl(result.cover_url ?? "");
      // Publisher and publish_year intentionally NOT auto-filled (D-03)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    let valid = true;

    if (!title.trim()) {
      setTitleError("Title is required.");
      valid = false;
    } else {
      setTitleError("");
    }
    if (!author.trim()) {
      setAuthorError("Author is required.");
      valid = false;
    } else {
      setAuthorError("");
    }

    if (!valid) return;

    const payload: BookCreatePayload = {
      title: title.trim(),
      author: author.trim(),
    };
    if (isbn.trim()) payload.isbn = isbn.trim();
    if (description.trim()) payload.description = description.trim();
    if (publisher.trim()) payload.publisher = publisher.trim();
    const yearInt = parseInt(publishYear, 10);
    if (publishYear.trim() && !isNaN(yearInt)) {
      payload.publish_year = yearInt;
    }
    if (coverUrl.trim()) payload.cover_url = coverUrl.trim();

    createMutation.mutate(payload);
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-semibold text-gray-900 mb-6">Add Book</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {/* ISBN + Fetch */}
        <div className="flex flex-col gap-1">
          <Label htmlFor="isbn">ISBN</Label>
          <Input
            id="isbn"
            placeholder="e.g. 9780140449136"
            value={isbn}
            onChange={(e) => setIsbn(e.target.value)}
          />
          <div className="mt-1">
            <ISBNFetchButton isbn={isbn} onResult={handleFetchResult} />
          </div>
        </div>

        {/* Title */}
        <div className="flex flex-col gap-1">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            aria-required
          />
          {titleError && (
            <p className="text-red-600 text-xs mt-1">{titleError}</p>
          )}
        </div>

        {/* Author */}
        <div className="flex flex-col gap-1">
          <Label htmlFor="author">Author</Label>
          <Input
            id="author"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            aria-required
          />
          {authorError && (
            <p className="text-red-600 text-xs mt-1">{authorError}</p>
          )}
        </div>

        {/* Description */}
        <div className="flex flex-col gap-1">
          <Label htmlFor="description">Description</Label>
          <textarea
            id="description"
            className="w-full border rounded px-3 py-2 text-sm"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {/* Publisher */}
        <div className="flex flex-col gap-1">
          <Label htmlFor="publisher">Publisher</Label>
          <Input
            id="publisher"
            value={publisher}
            onChange={(e) => setPublisher(e.target.value)}
          />
        </div>

        {/* Publish Year */}
        <div className="flex flex-col gap-1">
          <Label htmlFor="publish_year">Publish Year</Label>
          <Input
            id="publish_year"
            type="number"
            value={publishYear}
            onChange={(e) => setPublishYear(e.target.value)}
          />
        </div>

        {/* Footer buttons */}
        <div className="flex gap-3 pt-2">
          <Button
            type="submit"
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={createMutation.isPending}
          >
            Save Book
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/librarian/books")}
          >
            Discard Book
          </Button>
        </div>
      </form>
    </div>
  );
}
