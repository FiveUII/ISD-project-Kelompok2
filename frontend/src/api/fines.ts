/**
 * Fines API client — functions for fine management (list, pay, waive).
 * Uses apiClient (axios instance with JWT auth interceptor) from @/lib/api.
 */
import { apiClient } from "@/lib/api";

// ---------------------------------------------------------------------------
// TypeScript types
// ---------------------------------------------------------------------------

export interface FineItem {
  id: number;
  loan_id: number;
  amount: number;
  days_overdue: number;
  status: string;
  waiver_reason: string | null;
  created_at: string;
  loan: {
    id: number;
    due_date: string;
    returned_at: string | null;
    borrower: { id: number; email: string; full_name: string | null };
    book: { id: number; title: string };
  };
}

export interface FinesListResponse {
  items: FineItem[];
  total: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * GET /api/librarian/fines — list fines (paginated, optional status filter).
 */
export async function getLibrarianFines(
  page = 1,
  pageSize = 20,
  statusFilter?: string
): Promise<FinesListResponse> {
  const params: Record<string, string | number> = {
    page,
    page_size: pageSize,
  };
  if (statusFilter) {
    params.status = statusFilter;
  }
  const response = await apiClient.get<FinesListResponse>("/librarian/fines", {
    params,
  });
  return response.data;
}

/**
 * PATCH /api/librarian/fines/{fineId}/pay — mark a fine as paid.
 */
export async function payFine(fineId: number): Promise<FineItem> {
  const response = await apiClient.patch<FineItem>(
    `/librarian/fines/${fineId}/pay`
  );
  return response.data;
}

/**
 * PATCH /api/librarian/fines/{fineId}/waive — waive a fine with a reason.
 */
export async function waiveFine(
  fineId: number,
  reason: string
): Promise<FineItem> {
  const response = await apiClient.patch<FineItem>(
    `/librarian/fines/${fineId}/waive`,
    { reason }
  );
  return response.data;
}
