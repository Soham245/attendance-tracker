import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from '../layouts/AppLayout.jsx';
import Login from '../pages/Login.jsx';
import Dashboard from '../pages/Dashboard.jsx';
import Students from '../pages/Students.jsx';
import Training from '../pages/Training.jsx';
import LiveAttendance from '../pages/LiveAttendance.jsx';
import AttendanceHistory from '../pages/AttendanceHistory.jsx';
import UsersPage from '../pages/Users.jsx';
import ClassesPage from '../pages/Classes.jsx';
import SessionHistory from '../pages/SessionHistory.jsx';
import SessionDetail from '../pages/SessionDetail.jsx';
import ChangePassword from '../pages/ChangePassword.jsx';
import Profile from '../pages/Profile.jsx';
import NotFound from '../pages/NotFound.jsx';
import ProtectedRoute from './ProtectedRoute.jsx';
import AdminRoute from './AdminRoute.jsx';
import { useAuth } from '../hooks/useAuth.js';

function LoginGate({ children }) {
  // Bounce already-authenticated users away from /login.
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <LoginGate>
            <Login />
          </LoginGate>
        }
      />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/students" element={<Students />} />
          <Route path="/live" element={<LiveAttendance />} />
          <Route path="/attendance" element={<AttendanceHistory />} />
          <Route path="/sessions" element={<SessionHistory />} />
          <Route path="/sessions/:sessionId" element={<SessionDetail />} />
          {/* Admin-only pages */}
          <Route element={<AdminRoute />}>
            <Route path="/training" element={<Training />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/classes" element={<ClassesPage />} />
          </Route>
          <Route path="/profile" element={<Profile />} />
          <Route path="/change-password" element={<ChangePassword />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
