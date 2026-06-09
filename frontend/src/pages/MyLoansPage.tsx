/**
 * MyLoansPage — student's active loans at /my-loans.
 * Displays a card list of all non-returned loans for the logged-in student.
 * Shows book title, due date, and a red "Overdue" badge when is_overdue=true.
 * Empty state: "No active loans. Browse the catalog to find a book."
 *
 * Phase 3 — delivers LOAN-03 (overdue flag visible to students) and LOAN-04 (student loan view).
 * user_id always from JWT sub via get_current_user — client never passes user_id (T-03-01).
 */
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { getMyLoans } from "../api/loans";

export default function MyLoansPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["my-loans"],
    queryFn: getMyLoans,
  });

  const loans = data?.items ?? [];

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">My Loans</h1>

      {isLoading && (
        <div className="flex flex-col gap-4">
          {/* Skeleton placeholders while loading */}
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-24 rounded-xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-sm text-red-600">Failed to load your loans.</p>
      )}

      {!isLoading && !isError && loans.length === 0 && (
        <p className="text-sm text-gray-600">
          No active loans.{" "}
          <Link to="/catalog" className="text-blue-600 hover:underline">
            Browse the catalog to find a book.
          </Link>
        </p>
      )}

      {!isLoading && !isError && loans.length > 0 && (
        <div className="flex flex-col gap-4">
          {loans.map((loan) => (
            <Card key={loan.id} className="bg-white border border-gray-200 shadow-sm">
              <CardContent className="py-4 px-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex flex-col gap-1 min-w-0">
                    {/* Book title (author not in LoanItem — API returns book.title only) */}
                    <h3 className="text-lg font-semibold text-gray-900 leading-snug">
                      {loan.book.title}
                    </h3>
                    {/* Due date */}
                    <p className="text-sm text-gray-500">
                      Due:{" "}
                      {new Date(loan.due_date).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </p>
                  </div>
                  {/* Overdue badge (D-11) */}
                  {loan.is_overdue && (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700 shrink-0">
                      Overdue
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
