/**
 * Application root with React Router routes.
 * Auth routes added in Plan 02; password reset routes added in Plan 03.
 * Catalog routes wired in Phase 02 Plan 03 — real page components replace Wave 0 stubs.
 *
 * Route structure:
 *   Public (no auth required): /, /register, /login, /verify-email, /forgot-password, /reset-password
 *   Authenticated (AppLayout): /catalog
 *   Librarian-only (AppLayout requireLibrarian): /librarian/books, /librarian/books/new, /librarian/books/:id
 */
import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import Landing from "./pages/Landing";
import Register from "./pages/Register";
import Login from "./pages/Login";
import VerifyEmail from "./pages/VerifyEmail";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import CatalogPage from "./pages/CatalogPage";
import LibrarianBooksPage from "./pages/LibrarianBooksPage";
import AddBookPage from "./pages/AddBookPage";
import BookDetailPage from "./pages/BookDetailPage";

export default function App() {
  return (
    <Routes>
      {/* Public routes — outside AppLayout */}
      <Route path="/" element={<Landing />} />
      <Route path="/register" element={<Register />} />
      <Route path="/login" element={<Login />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Authenticated routes — all roles */}
      <Route element={<AppLayout />}>
        <Route path="/catalog" element={<CatalogPage />} />
      </Route>

      {/* Librarian-only routes */}
      <Route element={<AppLayout requireLibrarian />}>
        <Route path="/librarian/books" element={<LibrarianBooksPage />} />
        <Route path="/librarian/books/new" element={<AddBookPage />} />
        <Route path="/librarian/books/:id" element={<BookDetailPage />} />
      </Route>
    </Routes>
  );
}
