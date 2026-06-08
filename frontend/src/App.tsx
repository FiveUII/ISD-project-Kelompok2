/**
 * Application root with React Router routes.
 * Subsequent phases add more routes here.
 */
import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
    </Routes>
  );
}
