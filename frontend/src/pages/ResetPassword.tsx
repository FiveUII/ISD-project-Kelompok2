/**
 * Reset Password page — set a new password using the emailed token (AUTH-03).
 *
 * Flow:
 *   1. Read `token` query param from URL (/reset-password?token=...)
 *   2. User enters new password (min 8 chars)
 *   3. POST /auth/reset-password with token + new_password
 *   4. On success: redirect to /login with a success message
 *   5. On 400: show "Invalid or expired reset link"
 */
import { useState, FormEvent } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { apiClient } from "../lib/api";
import { AxiosError } from "axios";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Guard: no token in URL
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow rounded-lg p-8 text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Invalid reset link</h2>
          <p className="text-gray-500 mb-6">
            This password reset link is missing a token. Please request a new reset link.
          </p>
          <Link to="/forgot-password" className="text-blue-600 hover:underline text-sm">
            Request a new reset link
          </Link>
        </div>
      </div>
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await apiClient.post("/auth/reset-password", {
        token,
        new_password: newPassword,
      });

      // Redirect to login with a success indicator in the URL
      navigate("/login?reset=success");
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>;
      if (axiosErr.response?.status === 400) {
        setError(
          "This reset link is invalid or has already been used. Please request a new one."
        );
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Set a new password</h2>
        <p className="text-gray-500 text-sm mb-6">
          Choose a strong password (at least 8 characters).
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-1">
              New password
            </label>
            <input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm new password
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-md transition-colors"
          >
            {loading ? "Saving..." : "Set new password"}
          </button>
        </form>

        <p className="mt-4 text-sm text-center text-gray-600">
          Link expired?{" "}
          <Link to="/forgot-password" className="text-blue-600 hover:underline">
            Request a new one
          </Link>
        </p>
      </div>
    </div>
  );
}
