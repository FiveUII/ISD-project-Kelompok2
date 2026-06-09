/**
 * BookSearchCard — catalog search result card.
 * Shows cover thumbnail (or placeholder), title, author, ISBN, description snippet,
 * and an AvailabilityBadge.
 */
import { BookOpen } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import AvailabilityBadge from "./AvailabilityBadge";

interface BookSearchCardProps {
  book: {
    id: number;
    title: string;
    author: string;
    isbn: string | null;
    cover_url: string | null;
    available_count: number;
    description: string | null;
  };
}

export default function BookSearchCard({ book }: BookSearchCardProps) {
  const snippet =
    book.description && book.description.length > 150
      ? book.description.slice(0, 150) + "…"
      : (book.description ?? null);

  return (
    <Card className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <CardContent className="p-0">
        <div className="flex gap-4">
          {/* Cover or placeholder */}
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={`Cover of ${book.title}`}
              className="w-16 h-20 object-cover rounded flex-shrink-0"
            />
          ) : (
            <div className="w-16 h-20 bg-gray-100 rounded flex items-center justify-center flex-shrink-0">
              <BookOpen className="w-6 h-6 text-gray-400" />
            </div>
          )}

          {/* Book info */}
          <div className="flex flex-col gap-1 min-w-0">
            <h3 className="text-xl font-semibold text-gray-900 leading-tight">
              {book.title}
            </h3>
            <p className="text-sm text-gray-600">{book.author}</p>
            {book.isbn && (
              <p className="text-xs text-gray-400">ISBN: {book.isbn}</p>
            )}
            {snippet && (
              <p className="text-sm text-gray-500 mt-1">{snippet}</p>
            )}
            <div className="mt-2">
              <AvailabilityBadge count={book.available_count} />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
