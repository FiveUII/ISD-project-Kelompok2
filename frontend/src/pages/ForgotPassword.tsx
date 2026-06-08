/**
 * Forgot Password page — request a password-reset link (AUTH-03).
 *
 * Flow:
 *   1. User enters email address
 *   2. POST /auth/forgot-password
 *   3. Always show "If that email exists, a reset link has been sent." (no user enumeration)
 */
import { useState, FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../lib/api";
import { AxiosError } from "axios";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await apiClient.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>;
      if (axiosErr.response) {
        setError("Something went wrong. Please try again.");
      } else {
        setError("Network error. Please check your connection and try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow rounded-lg p-8 text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Check your inbox</h2>
          <p className="text-gray-600 mb-6">
            If that email exists in our system, a password reset link has been sent.
            Check your inbox (and spam folder) and follow the link to set a new password.
          </p>
          <Link
            to="/login"
            className="text-blue-600 hover:underline text-sm"
          >
            Back to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Reset your password</h2>
        <p className="text-gray-500 text-sm mb-6">
          Enter your email address and we'll send you a reset link.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="jane@university.edu"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-md transition-colors"
          >
            {loading ? "Sending..." : "Send reset link"}
          </button>
        </form>

        <p className="mt-4 text-sm text-center text-gray-600">
          Remembered your password?{" "}
          <Link to="/login" className="text-blue-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
