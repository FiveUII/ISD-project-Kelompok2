/**
 * Loans API client — functions for checkout, return, and loan queries.
 * Uses apiClient (axios instance with JWT auth interceptor) from @/lib/api.
 */
import { apiClient } from "@/lib/api";

// ---------------------------------------------------------------------------
// TypeScript types
// ---------------------------------------------------------------------------

export interface LoanItem {
  id: number;
  copy_id: number;
  copy: { id: number; barcode: string | null };
  book: { id: number; title: string };
  borrower: { id: number; email: string; full_name: string | null };
  checked_out_at: string;
  due_date: string;
  returned_at: string | null;
  is_overdue: boolean;
}

export interface LoansListResponse {
  items: LoanItem[];
  total: number;
}

export interface StudentUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_email_verified: boolean;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * GET /api/librarian/loans — list active loans.
 * overdue=true filters to loans past due date.
 */
export async function getLibrarianLoans(
  overdue = false,
  page = 1,
  pageSize = 20
): Promise<LoansListResponse> {
  const response = await apiClient.get<LoansListResponse>("/librarian/loans", {
    params: { overdue, page, page_size: pageSize },
  });
  return response.data;
}

/**
 * PATCH /api/librarian/loans/{loanId}/return — mark a loan returned.
 */
export async function returnLoan(loanId: number): Promise<LoanItem> {
  const response = await apiClient.patch<LoanItem>(
    `/librarian/loans/${loanId}/return`
  );
  return response.data;
}

/**
 * POST /api/librarian/loans/checkout — check out a copy to a student.
 */
export async function checkoutCopy(
  copyId: number,
  userId: number
): Promise<LoanItem> {
  const response = await apiClient.post<LoanItem>("/librarian/loans/checkout", {
    copy_id: copyId,
    user_id: userId,
  });
  return response.data;
}

/**
 * GET /api/admin/users?role=student&search=query — search students for checkout.
 * Returns up to 20 matching student accounts.
 */
export async function searchStudents(query: string): Promise<StudentUser[]> {
  const response = await apiClient.get<StudentUser[]>("/admin/users", {
    params: { role: "student", search: query },
  });
  return response.data;
}

/**
 * GET /api/loans/my — get the current student's active loans.
 */
export async function getMyLoans(): Promise<LoansListResponse> {
  const response = await apiClient.get<LoansListResponse>("/loans/my");
  return response.data;
}
