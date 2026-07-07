import React, {
  createContext,
  useState,
  useContext,
  useEffect,
  useRef,
} from 'react';

const AuthContext = createContext();

// Honor VITE_API_URL (baked at build time) with the deployed backend as
// fallback, matching services/api.js. Strip a trailing /api/v1 if present,
// since the auth routes below already include the full path.
const API_BASE_URL = (import.meta.env.VITE_API_URL || "https://capstone-be-yxzd.onrender.com")
  .replace(/\/api\/v1\/?$/, "");

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
        console.error('Error parsing stored user data:', e);
        localStorage.clear();
      }
    }

    initialized.current = true;
    setLoading(false);
  }, []);

  // =====================
  // LOGIN - Redirect to Google OAuth
  // =====================
  const login = () => {
    try {
      const url = `${API_BASE_URL}/api/v1/auth/google/login`;
      console.log('🔐 Redirecting to Google login:', url);
      window.location.href = url;
    } catch (error) {
      console.error('❌ Login error:', error);
      // You might want to show an error message to the user here
    }
  };

  // =====================
  // LOGIN WITH POPUP (Alternative - cleaner UX)
  // =====================
  const loginWithPopup = () => {
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      `${API_BASE_URL}/api/v1/auth/google/login`,
      'Google Login',
      `width=${width},height=${height},left=${left},top=${top}`
    );

    // Listen for messages from the popup
    const handleMessage = (event) => {
      // Make sure the message is from your domain
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === 'auth_success') {
        const { token, user } = event.data;
        setAuth(token, user);
        popup.close();
        window.removeEventListener('message', handleMessage);
      }
    };

    window.addEventListener('message', handleMessage);
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
    console.log('✅ Setting auth for user:', userData?.email);
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(token);
    setUser(userData);
  };

  // =====================
  // CHECK IF TOKEN IS EXPIRED
  // =====================
  const isTokenExpired = () => {
    if (!token) return true;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 < Date.now();
    } catch (e) {
      return true;
    }
  };

  // =====================
  // REFRESH TOKEN (Optional)
  // =====================
  const refreshToken = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setAuth(data.token, user);
        return data.token;
      } else {
        logout();
        return null;
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      logout();
      return null;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        loginWithPopup,
        logout,
        setAuth,
        refreshToken,
        isTokenExpired,
        isAuthenticated: !!user && !!token && !isTokenExpired(),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};