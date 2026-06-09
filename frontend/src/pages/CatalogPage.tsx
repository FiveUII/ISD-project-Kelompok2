/**
 * CatalogPage — student-facing book search page at /catalog.
 * URL-driven search: /catalog?q=hemingway&page=1
 * Search fires on button click or Enter key — NOT real-time.
 * Uses TanStack Query v5 with keepPreviousData for pagination.
 */
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api";
import BookSearchCard from "../components/BookSearchCard";
import SearchPagination from "../components/SearchPagination";

interface BookItem {
  id: number;
  title: string;
  author: string;
  isbn: string | null;
  cover_url: string | null;
  available_count: number;
  description: string | null;
}

interface BookListResponse {
  items: BookItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export default function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const page = Number(searchParams.get("page") ?? "1");

  // Local input state initialized from URL param
  const [inputValue, setInputValue] = useState(q);

  const { data, isLoading } = useQuery<BookListResponse>({
    queryKey: ["books", { q, page, page_size: 20 }],
    queryFn: () =>
      apiClient
        .get("/books", { params: { q: q || undefined, page, page_size: 20 } })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
    enabled: q !== "",
  });

  function handleSearch() {
    setSearchParams({ q: inputValue, page: "1" });
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-semibold text-gray-900 mb-6">Book Catalog</h1>

      {/* Search bar */}
      <div className="max-w-2xl mx-auto mb-8">
        <Input
          placeholder="Search by title, author, or ISBN..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
          className="w-full"
        />
        <Button
          onClick={handleSearch}
          className="mt-2 bg-blue-600 text-white hover:bg-blue-700"
        >
          Search Catalog
        </Button>
      </div>

      {/* States */}
      {q === "" && (
        <div className="text-center py-16">
          <p className="text-xl font-semibold text-gray-700">Search the catalog</p>
          <p className="text-sm text-gray-500 mt-2">
            Enter a title, author, or ISBN to find books.
          </p>
        </div>
      )}

      {q !== "" && isLoading && (
        <div className="flex flex-col gap-4 max-w-2xl mx-auto">
          <Skeleton className="h-24 w-full rounded-lg" />
          <Skeleton className="h-24 w-full rounded-lg" />
          <Skeleton className="h-24 w-full rounded-lg" />
        </div>
      )}

      {q !== "" && !isLoading && data && data.items.length === 0 && (
        <div className="text-center py-16">
          <p className="text-xl font-semibold text-gray-700">No books found</p>
          <p className="text-sm text-gray-500 mt-2">
            Try a different title, author, or ISBN.
          </p>
        </div>
      )}

      {q !== "" && !isLoading && data && data.items.length > 0 && (
        <>
          <div className="flex flex-col gap-4 max-w-2xl mx-auto">
            {data.items.map((book) => (
              <BookSearchCard key={book.id} book={book} />
            ))}
          </div>

          {data.pages > 1 && (
            <div className="mt-8">
              <SearchPagination
                page={page}
                pages={data.pages}
                onPageChange={(p) =>
                  setSearchParams({ q, page: String(p) })
                }
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
