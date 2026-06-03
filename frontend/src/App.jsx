import { HashRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext.jsx';
import { ClassProvider } from './context/ClassContext.jsx';
import { ToastProvider } from './context/ToastContext.jsx';
import AppRoutes from './routes/AppRoutes.jsx';

// HashRouter keeps deep links working both in the browser (Vite dev) and
// when the bundle is loaded from Electron's `file://` shell.
export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <ClassProvider>
          <HashRouter>
            <AppRoutes />
          </HashRouter>
        </ClassProvider>
      </ToastProvider>
    </AuthProvider>
  );
}
