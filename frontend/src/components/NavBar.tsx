/**
 * Top navigation bar for the authenticated shell.
 * Renders role-aware links: all users see "Catalog"; librarians also see "Manage Books".
 * Active link indicated by blue underline. Logout clears auth store and redirects to /login.
 */
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

export default function NavBar() {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function linkClass(href: string) {
    const isActive = location.pathname === href || location.pathname.startsWith(href + "/");
    return isActive
      ? "text-blue-600 font-semibold border-b-2 border-blue-600 text-sm"
      : "text-gray-600 hover:text-gray-900 text-sm font-semibold";
  }

  return (
    <header className="h-14 bg-white border-b border-gray-200 w-full">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-full">
        {/* Left: Logo + nav links */}
        <div className="flex items-center gap-6">
          <Link to="/catalog" className="font-semibold text-gray-900">
            Library
          </Link>
          <nav className="flex items-center gap-4">
            <Link to="/catalog" className={linkClass("/catalog")}>
              Catalog
            </Link>
            {user?.role === "student" && (
              <Link to="/my-loans" className={linkClass("/my-loans")}>
                My Loans
              </Link>
            )}
            {user?.role === "librarian" && (
              <Link to="/librarian/books" className={linkClass("/librarian/books")}>
                Manage Books
              </Link>
            )}
            {user?.role === "librarian" && (
              <Link to="/librarian/loans" className={linkClass("/librarian/loans")}>
                Loans
              </Link>
            )}
            {user?.role === "librarian" && (
              <Link to="/librarian/fines" className={linkClass("/librarian/fines")}>
                Fines
              </Link>
            )}
          </nav>
        </div>

        {/* Right: Logout */}
        <button
          onClick={handleLogout}
          className="text-gray-500 hover:text-gray-700 text-sm"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
