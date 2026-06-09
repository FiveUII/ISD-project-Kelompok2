/**
 * Authenticated layout shell wrapping all protected routes.
 *
 * Auth guard: redirects unauthenticated users to /login.
 * Role guard: if requireLibrarian=true and user is not a librarian,
 *   redirects to /catalog (user is authenticated but unauthorized).
 *
 * Individual pages apply their own padding (max-w-7xl mx-auto px-6 py-8).
 */
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import NavBar from "./NavBar";

interface AppLayoutProps {
  requireLibrarian?: boolean;
}

export default function AppLayout({ requireLibrarian = false }: AppLayoutProps) {
  const { token, user } = useAuthStore();

  // Not authenticated — redirect to login
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Authenticated but not a librarian — redirect to catalog (not login)
  if (requireLibrarian && user?.role !== "librarian") {
    return <Navigate to="/catalog" replace />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
