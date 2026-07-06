import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const userParam = params.get('user');

    console.log('🔐 Processing authentication callback...');

    if (!token || !userParam) {
      console.error('❌ Missing auth data');
      navigate('/login', { replace: true });
      return;
    }
    try {
      const user = JSON.parse(decodeURIComponent(userParam));
      console.log(`✅ Authenticated: ${user.email}`);
      
      // Navigate FIRST - this will unmount the component
      navigate('/dashboard', { replace: true });
      
      // Then set auth (this will run in the background)
      // The component will be unmounted by then
      setTimeout(() => {
        setAuth(token, user);
        console.log('✅ Auth set in background');
      }, 0);
      
    } catch (err) {
      console.error('❌ Auth error:', err);
      navigate('/login', { replace: true });
    }
  }, [navigate, setAuth]);

  return (
    <div style={styles.container}>
      <div style={styles.loadingContainer}>
        <h2 style={styles.loadingTitle}>Completing login...</h2>
        <p style={styles.loadingMessage}>Please wait...</p>
        <div style={styles.spinner}>⏳</div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    textAlign: 'center',
    padding: '40px',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
  },
  loadingTitle: {
    margin: '0 0 10px 0',
    color: '#333',
    fontSize: '24px',
  },
  loadingMessage: {
    margin: '0 0 20px 0',
    color: '#666',
    fontSize: '16px',
  },
  spinner: {
    fontSize: '32px',
    animation: 'spin 1s linear infinite',
  },
};

// Add spin animation
const styleSheet = document.createElement("style");
styleSheet.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);

export default AuthCallback;