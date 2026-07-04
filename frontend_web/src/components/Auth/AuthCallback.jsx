import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Auth.css';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { handleAuthCallback } = useAuth();
  const [error, setError] = useState(null);

useEffect(() => {
  console.log("🔄 AuthCallback mounted");
  console.log("🌐 Full URL:", window.location.href);
  console.log("🔎 Search params:", window.location.search);

  const params = new URLSearchParams(window.location.search);

  const token = params.get('token');
  const userDataParam = params.get('user');

  console.log("🔑 Token exists:", !!token);
  console.log("👤 User param exists:", !!userDataParam);

  if (!token || !userDataParam) {
    console.error("❌ Missing auth data");
    console.log("Token value:", token);
    console.log("User value:", userDataParam);

    setError('Missing authentication data');

    setTimeout(() => {
      console.log("↩️ Redirecting to login...");
      window.location.href = '/login';
    }, 3000);

    return;
  }

  try {
    console.log("📦 Raw user param:", userDataParam);

    const decoded = decodeURIComponent(userDataParam);
    console.log("🧾 Decoded user JSON string:", decoded);

    const user = JSON.parse(decoded);
    console.log("✅ Parsed user object:", user);

    console.log("💾 Saving to localStorage...");
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));

    console.log("🔐 Calling handleAuthCallback...");
    handleAuthCallback(token, user);

    console.log("🚀 Redirecting to dashboard...");
    window.location.href = window.location.origin + '/dashboard';

  } catch (error) {
    console.error("💥 Auth callback error:", error);
    console.log("Raw user param was:", userDataParam);

    setError(`Auth failed: ${error.message}`);

    setTimeout(() => {
      console.log("↩️ Redirecting to login after error...");
      window.location.href = '/login';
    }, 3000);
  }
}, [handleAuthCallback]);
  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        padding: '20px',
        background: '#f7fafc'
      }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>❌</div>
        <h1 style={{ color: '#2d3748', marginBottom: '8px' }}>Authentication Failed</h1>
        <p style={{ color: '#718096', textAlign: 'center', maxWidth: '400px' }}>{error}</p>
        <p style={{ fontSize: '14px', color: '#a0aec0', marginTop: '12px' }}>
          Redirecting to login...
        </p>
      </div>
    );
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center', 
      justifyContent: 'center', 
      height: '100vh',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      background: '#f7fafc'
    }}>
      <div style={{ 
        width: '48px', 
        height: '48px', 
        border: '4px solid #e2e8f0', 
        borderTopColor: '#667eea', 
        borderRadius: '50%', 
        animation: 'spin 0.8s linear infinite',
        marginBottom: '20px'
      }}></div>
      <h2 style={{ color: '#2d3748' }}>Completing Authentication...</h2>
      <p style={{ color: '#718096', fontSize: '14px', marginTop: '8px' }}>
        Please wait while we verify your credentials
      </p>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default AuthCallback;