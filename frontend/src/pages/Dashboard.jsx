import { useAuth } from '../hooks/useAuth.js';
import AdminDashboard from '../components/dashboard/AdminDashboard.jsx';
import FacultyDashboard from '../components/dashboard/FacultyDashboard.jsx';

export default function Dashboard() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  return isAdmin ? <AdminDashboard /> : <FacultyDashboard />;
}
