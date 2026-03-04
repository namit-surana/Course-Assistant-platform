import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

// Pages (to be built)
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import CoursePage from "./pages/CoursePage";
import AssignmentPage from "./pages/AssignmentPage";
import SubmitPage from "./pages/SubmitPage";
import FeedbackPage from "./pages/FeedbackPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"                                      element={<LoginPage />} />
        <Route path="/dashboard"                                  element={<DashboardPage />} />
        <Route path="/courses/:courseId"                          element={<CoursePage />} />
        <Route path="/courses/:courseId/assignments/:assignmentId" element={<AssignmentPage />} />
        <Route path="/courses/:courseId/assignments/:assignmentId/submit" element={<SubmitPage />} />
        <Route path="/feedback/:submissionId"                     element={<FeedbackPage />} />
        <Route path="*"                                           element={<Navigate to="/dashboard" />} />
      </Routes>
    </BrowserRouter>
  );
}
