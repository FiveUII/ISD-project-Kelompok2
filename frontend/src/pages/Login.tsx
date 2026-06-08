/**
 * Login page — email + password authentication (AUTH-01).
 *
 * Flow:
 *   1. POST /auth/login with credentials
 *   2. On 200: store token + user in Zustand (persisted to localStorage) → redirect to /
 *   3. On 403: show "Please verify your email first" (D-01)
 *   4. On 401: show "Invalid email or password"
 */
import { useState, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { AxiosError } from "axios";

interface LoginResponse {
  access_token: string;
  token_type: string;
}

interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: "student" | "librarian";
  is_email_verified: boolean;
}

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Step 1: authenticate and get token
      const loginResp = await apiClient.post<LoginResponse>("/auth/login", {
        email,
        password,
      });
      const { access_token } = loginResp.data;

      // Step 2: fetch full user profile using the new token
      const meResp = await apiClient.get<UserProfile>("/auth/me", {
        headers: { Authorization: `Bearer ${access_token}` },
      });

      // Step 3: persist token + user in Zustand (localStorage)
      setAuth(access_token, meResp.data);

      // Step 4: redirect to the landing page
      navigate("/");
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>;
      if (axiosErr.response?.status === 403) {
        setError("Please verify your email first. Check your inbox for the verification link.");
      } else if (axiosErr.response?.status === 401) {
        setError("Invalid email or password.");
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Log in</h2>

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

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-md transition-colors"
          >
            {loading ? "Logging in..." : "Log in"}
          </button>
        </form>

        <p className="mt-4 text-sm text-center text-gray-600">
          No account?{" "}
          <Link to="/register" className="text-blue-600 hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
