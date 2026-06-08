/**
 * Landing page — Walking Skeleton proof of end-to-end connectivity.
 *
 * Fetches GET /api/health/db via TanStack Query, which reads the seeded
 * loan_period_days from PostgreSQL through FastAPI → SQLAlchemy → asyncpg.
 *
 * Renders the loan_period_days value to prove Browser → Nginx → FastAPI → PostgreSQL works.
 */
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/api";

interface HealthDbResponse {
  status: string;
  loan_period_days: number;
}

async function fetchHealthDb(): Promise<HealthDbResponse> {
  const response = await apiClient.get<HealthDbResponse>("/health/db");
  return response.data;
}

export default function Landing() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["health", "db"],
    queryFn: fetchHealthDb,
  });

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Library Management System
        </h1>
        <p className="text-gray-500 text-sm mb-6">
          School Library — Walking Skeleton
        </p>

        <div className="border rounded-lg p-4 bg-gray-50">
          <h2 className="text-sm font-medium text-gray-700 mb-2">
            System Status
          </h2>

          {isLoading && (
            <p className="text-gray-500 text-sm">Connecting to database...</p>
          )}

          {isError && (
            <div className="text-red-600 text-sm">
              <p className="font-medium">Database connection failed</p>
              <p className="text-xs mt-1 text-red-400">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
            </div>
          )}

          {data && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>
                <span className="text-sm text-green-700 font-medium">
                  Database connected
                </span>
              </div>
              <p className="text-gray-700 text-sm">
                Loan period:{" "}
                <span className="font-semibold text-gray-900">
                  {data.loan_period_days} days
                </span>
              </p>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-400 mt-4">
          This page reads <code className="bg-gray-100 px-1 rounded">/api/health/db</code>{" "}
          to prove the full stack (Nginx → FastAPI → PostgreSQL) is working.
        </p>
      </div>
    </div>
  );
}
