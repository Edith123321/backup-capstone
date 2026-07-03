// frontend_web/src/context/AuthContext.jsx
import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import axios from 'axios';

const AuthContext = createContext();
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001' || 'https://backup-capstone-mbq6.onrender.com';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);
  
  // Use a ref to track if verification has been done
  const verificationDone = useRef(false);

  useEffect(() => {
    // Only run once
    if (verificationDone.current) {
      return;
    }
    
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    
    console.log('🔍 AuthProvider: Checking localStorage...');
    console.log('🔍 AuthProvider: Token present:', !!storedToken);
    console.log('🔍 AuthProvider: User present:', !!storedUser);
    
    if (storedToken && storedUser) {
      setToken(storedToken);
      try {
        const userData = JSON.parse(storedUser);
        setUser(userData);
        console.log('✅ AuthProvider: User loaded from localStorage:', userData.email);
        verificationDone.current = true;
        setLoading(false);
      } catch (error) {
        console.error('Failed to parse stored user:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setLoading(false);
      }
    } else {
      console.log('🔍 AuthProvider: No stored auth data');
      setLoading(false);
    }
  }, []); // Empty dependency - only run once

  const login = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/google/login`);
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const logout = () => {
    console.log('🔍 Logging out...');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    verificationDone.current = false;
    window.location.href = '/';
  };

  const handleAuthCallback = (token, userData) => {
    console.log('🔄 handleAuthCallback called');
    console.log('📝 Token present:', !!token);
    console.log('👤 User data:', userData);
    
    if (token && userData) {
      // Save to localStorage
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Update state
      setToken(token);
      setUser(userData);
      verificationDone.current = true;
      
      console.log('✅ Auth state updated successfully');
      
      // Use window.location for a hard redirect
      window.location.href = '/dashboard';
    } else {
      console.error('❌ Invalid auth data received');
      window.location.href = '/login?error=Invalid auth data';
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      token,
      login,
      logout,
      handleAuthCallback,
      isAuthenticated: !!user
    }}>
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