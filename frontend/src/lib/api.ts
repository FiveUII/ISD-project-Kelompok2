/**
 * Axios API client instance.
 * All requests use /api as the base URL — Nginx proxies this to the FastAPI backend.
 *
 * Request interceptor attaches the JWT Bearer token from the Zustand auth store
 * (persisted in localStorage as "lms-auth") when a token is present.
 */
import axios from "axios";
import { useAuthStore } from "../store/auth";

export const apiClient = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT Bearer token from Zustand auth store on every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
