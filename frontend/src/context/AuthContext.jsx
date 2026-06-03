import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import { onUnauthorized, tokenStore } from '../services/api.js';
import * as authService from '../services/authService.js';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => tokenStore.get());
  // `loading` covers the initial /auth/me restore; `pending` covers the
  // explicit login submit so the form can show a spinner without blocking
  // the rest of the shell.
  const [loading, setLoading] = useState(true);

  // Restore session on mount.
  useEffect(() => {
    let cancelled = false;
    const stored = tokenStore.get();
    if (!stored) {
      setLoading(false);
      return undefined;
    }

    authService
      .fetchCurrentUser()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        if (!cancelled) {
          tokenStore.clear();
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Any 401 from the API layer (token expired, revoked, etc.) -> sign out.
  useEffect(
    () =>
      onUnauthorized(() => {
        setToken(null);
        setUser(null);
      }),
    [],
  );

  const login = useCallback(async (username, password) => {
    const tokenData = await authService.login(username, password);
    tokenStore.set(tokenData.access_token);
    setToken(tokenData.access_token);
    const me = await authService.fetchCurrentUser();
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setToken(null);
    setUser(null);
  }, []);

  /** Re-fetch /auth/me to update user state (e.g. after password change). */
  const refreshUser = useCallback(async () => {
    try {
      const me = await authService.fetchCurrentUser();
      setUser(me);
      return me;
    } catch {
      return null;
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      refreshUser,
    }),
    [user, token, loading, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
