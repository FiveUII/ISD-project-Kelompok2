/**
 * SearchPagination — Previous / Page N / Next pagination strip.
 * Previous disabled on page 1; Next disabled when page >= pages.
 * Current page label uses text-blue-600 font-semibold per D-05.
 */
import { Button } from "@/components/ui/button";

interface SearchPaginationProps {
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}

export default function SearchPagination({
  page,
  pages,
  onPageChange,
}: SearchPaginationProps) {
  return (
    <div className="flex items-center gap-3 justify-center">
      <Button
        variant="outline"
        disabled={page === 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>

      <span className="text-sm text-blue-600 font-semibold">
        Page {page}
      </span>

      <Button
        variant="outline"
        disabled={page >= pages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </div>
  );
}
