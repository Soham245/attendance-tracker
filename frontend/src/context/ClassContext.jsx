import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth.js';
import { fetchFacultyClasses } from '../services/userService.js';
import { fetchClasses } from '../services/classService.js';

const ClassContext = createContext(null);

const STORAGE_KEY = 'attendai_active_class';

/**
 * Provides the "active class" scope for both faculty and admin.
 *
 * - Faculty: loads their assigned classes.
 * - Admin: loads all classes from the system.
 *
 * Selecting a class scopes the entire app (sessions, students, attendance).
 *
 * - `classes`       – all available classes (with major/year/section)
 * - `activeClass`   – the currently selected class object (or null)
 * - `setActiveClass` – pick a class by its object (or null to clear)
 * - `loading`       – true while fetching class list
 * - `grouped`       – classes grouped by major: { [major]: [...classes] }
 */
export function ClassProvider({ children }) {
  const { user } = useAuth();
  const isFaculty = user?.role === 'faculty';
  const isAdmin = user?.role === 'admin';

  const [classes, setClasses] = useState([]);
  const [activeClass, setActiveClassState] = useState(null);
  const [loading, setLoading] = useState(false);

  // Load classes — faculty gets their assignments, admin gets all.
  useEffect(() => {
    if (!user?.id || (!isFaculty && !isAdmin)) {
      setClasses([]);
      setActiveClassState(null);
      return;
    }

    let cancelled = false;
    setLoading(true);

    const load = isAdmin
      ? fetchClasses().then((result) => {
          // Normalise admin class objects to the same shape as faculty assignments.
          return (result?.items ?? []).map((c) => ({
            class_id: c.id,
            class_code: c.class_code,
            major: c.major,
            year: c.year,
            section: c.section,
          }));
        })
      : fetchFacultyClasses(user.id).then((result) => result?.assignments ?? []);

    load
      .then((list) => {
        if (cancelled) return;
        setClasses(list);

        // Restore saved active class from localStorage.
        const savedId = Number(localStorage.getItem(STORAGE_KEY));
        const saved = list.find((c) => c.class_id === savedId);
        if (saved) {
          setActiveClassState(saved);
        } else if (list.length === 1) {
          // Auto-select if only one class.
          setActiveClassState(list[0]);
          localStorage.setItem(STORAGE_KEY, String(list[0].class_id));
        } else {
          setActiveClassState(null);
        }
      })
      .catch(() => {
        if (!cancelled) setClasses([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [isFaculty, isAdmin, user?.id]);

  const setActiveClass = useCallback((cls) => {
    setActiveClassState(cls);
    if (cls) {
      localStorage.setItem(STORAGE_KEY, String(cls.class_id));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  // Group classes by major — memoized to keep context value stable.
  const grouped = useMemo(
    () =>
      classes.reduce((acc, cls) => {
        const key = cls.major;
        if (!acc[key]) acc[key] = [];
        acc[key].push(cls);
        return acc;
      }, {}),
    [classes],
  );

  const value = useMemo(
    () => ({ classes, activeClass, setActiveClass, loading, grouped }),
    [classes, activeClass, setActiveClass, loading, grouped],
  );

  return (
    <ClassContext.Provider value={value}>
      {children}
    </ClassContext.Provider>
  );
}

export function useClassContext() {
  const ctx = useContext(ClassContext);
  if (!ctx) {
    throw new Error('useClassContext must be used inside <ClassProvider>');
  }
  return ctx;
}
