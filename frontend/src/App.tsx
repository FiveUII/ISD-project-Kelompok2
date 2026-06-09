/**
 * Application root with React Router routes.
 * Auth routes added in Plan 02; password reset routes added in Plan 03.
 * Catalog routes added in Phase 02 Plan 01 — wrapped in AppLayout shell.
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
        <Route path="/catalog" element={<div>Catalog coming soon</div>} />
      </Route>

      {/* Librarian-only routes */}
      <Route element={<AppLayout requireLibrarian />}>
        <Route path="/librarian/books" element={<div>Manage Books coming soon</div>} />
        <Route path="/librarian/books/new" element={<div>Add Book coming soon</div>} />
        <Route path="/librarian/books/:id" element={<div>Book Detail coming soon</div>} />
      </Route>
    </Routes>
  );
}
