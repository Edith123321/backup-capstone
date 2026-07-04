import React, {
  createContext,
  useState,
  useContext,
  useEffect,
  useRef,
} from 'react';

const AuthContext = createContext();

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://capstone-be-yxzd.onrender.com/api/v1';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;

    const t = localStorage.getItem('token');
    const u = localStorage.getItem('user');

    if (t && u) {
      try {
        setToken(t);
        setUser(JSON.parse(u));
      } catch (e) {
        localStorage.clear();
      }
    }

    initialized.current = true;
    setLoading(false);
  }, []);

  // =====================
  // LOGIN
  // =====================
  const login = () => {
    window.location.href = `${API_BASE_URL}/auth/google/login`;
  };

  // =====================
  // LOGOUT
  // =====================
  const logout = () => {
    localStorage.clear();
    setUser(null);
    setToken(null);
    window.location.href = '/login';
  };

  // =====================
  // SAVE AUTH ONLY (NO REDIRECT HERE)
  // =====================
  const setAuth = (token, userData) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(token);
    setUser(userData);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        setAuth,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);