// frontend_web/src/context/AuthContext.jsx
import React, {
  createContext,
  useState,
  useContext,
  useEffect,
  useRef,
} from 'react';

const AuthContext = createContext();

// =====================
// FIXED BASE URL (STRING ONLY)
// =====================
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://capstone-be-yxzd.onrender.com/api/v1';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  const verificationDone = useRef(false);

  // =====================
  // LOAD AUTH FROM STORAGE
  // =====================
  useEffect(() => {
    if (verificationDone.current) return;

    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');

    console.log('🔍 AuthProvider: Checking localStorage...');
    console.log('🔍 Token exists:', !!storedToken);
    console.log('🔍 User exists:', !!storedUser);

    if (storedToken && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);

        setToken(storedToken);
        setUser(parsedUser);

        verificationDone.current = true;
        setLoading(false);

        console.log('✅ Auth restored:', parsedUser.email);
      } catch (err) {
        console.error('❌ Failed to parse user:', err);

        localStorage.removeItem('token');
        localStorage.removeItem('user');

        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  }, []);

  // =====================
  // LOGIN (GOOGLE REDIRECT FIXED)
  // =====================
  const login = () => {
    const loginUrl = `${API_BASE_URL}/auth/google/login`;
    console.log('🚀 Redirecting to:', loginUrl);
    window.location.href = loginUrl;
  };

  // =====================
  // LOGOUT
  // =====================
  const logout = () => {
    console.log('🔍 Logging out...');

    localStorage.removeItem('token');
    localStorage.removeItem('user');

    setToken(null);
    setUser(null);
    verificationDone.current = false;

    window.location.href = '/';
  };

  // =====================
  // AUTH CALLBACK HANDLER
  // =====================
  const handleAuthCallback = (token, userData) => {
    console.log('🔄 Auth callback triggered');

    if (!token || !userData) {
      console.error('❌ Missing auth data');

      window.location.href = '/login?error=Invalid auth data';
      return;
    }

    try {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userData));

      setToken(token);
      setUser(userData);

      verificationDone.current = true;

      console.log('✅ Auth saved successfully');
      console.log('🚀 Redirecting to dashboard...');

      window.location.href = '/dashboard';
    } catch (err) {
      console.error('❌ Auth save failed:', err);

      window.location.href = '/login?error=Auth processing failed';
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        token,
        login,
        logout,
        handleAuthCallback,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// =====================
// HOOK
// =====================
export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
};