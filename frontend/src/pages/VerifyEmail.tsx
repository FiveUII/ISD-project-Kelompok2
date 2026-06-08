/**
 * VerifyEmail page — reads `token` from the URL query string and
 * calls GET /auth/verify-email?token=... to verify the user's email.
 *
 * On success: shows "Email verified — you can now log in" with link to /login.
 * On invalid/expired token: shows an error message.
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiClient } from "../lib/api";
import { AxiosError } from "axios";

type Status = "loading" | "success" | "error" | "missing-token";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<Status>(token ? "loading" : "missing-token");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    if (!token) return;

    apiClient
      .get(`/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(() => {
        setStatus("success");
      })
      .catch((err: AxiosError<{ detail: string }>) => {
        const detail = err.response?.data?.detail ?? "Verification failed.";
        setErrorMessage(detail);
        setStatus("error");
      });
  }, [token]);

  if (status === "missing-token") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow rounded-lg p-8 text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Invalid link</h2>
          <p className="text-gray-600 mb-6">
            No verification token found. Please use the link from your verification email.
          </p>
          <Link to="/register" className="text-blue-600 hover:underline">
            Back to registration
          </Link>
        </div>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow rounded-lg p-8 text-center">
          <p className="text-gray-600">Verifying your email...</p>
        </div>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow rounded-lg p-8 text-center">
          <h2 className="text-2xl font-bold text-green-600 mb-4">Email verified!</h2>
          <p className="text-gray-600 mb-6">
            Your email has been verified. You can now log in to your account.
          </p>
          <Link
            to="/login"
            className="inline-block py-2 px-6 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-colors"
          >
            Log in
          </Link>
        </div>
      </div>
    );
  }

  // error
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow rounded-lg p-8 text-center">
        <h2 className="text-2xl font-bold text-red-600 mb-4">Verification failed</h2>
        <p className="text-gray-600 mb-6">{errorMessage}</p>
        <p className="text-sm text-gray-500">
          The link may have expired or already been used.{" "}
          <Link to="/register" className="text-blue-600 hover:underline">
            Register again
          </Link>{" "}
          to get a new verification email.
        </p>
      </div>
    </div>
  );
}
