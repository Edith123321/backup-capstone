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

    // Check for missing data
    if (!token || !userParam) {
      console.error('❌ Missing token or user data');
      setError('Missing authentication data');
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);
      return;
    }

    try {
      // Decode and parse user data
      const decodedUser = decodeURIComponent(userParam);
      const user = JSON.parse(decodedUser);
      
      console.log(`✅ Authenticated as: ${user.email}`);
      
      // Set authentication
      setAuth(token, user);
      
      // Navigate to dashboard immediately
      navigate('/dashboard', { replace: true });
      
    } catch (err) {
      console.error('❌ Auth parse error:', err);
      setError('Failed to process authentication');
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 3000);
    }
  }, [navigate, setAuth]);

  // Show loading state while processing
  return (
    <div style={styles.container}>
      {error ? (
        <div style={styles.errorContainer}>
          <h2 style={styles.errorTitle}>Authentication Error</h2>
          <p style={styles.errorMessage}>{error}</p>
          <p style={styles.redirectMessage}>Redirecting to login...</p>
        </div>
      ) : (
        <div style={styles.loadingContainer}>
          <h2 style={styles.loadingTitle}>Completing login...</h2>
          <p style={styles.loadingMessage}>Please wait while we verify your credentials.</p>
          <div style={styles.spinner}>⏳</div>
        </div>
      )}
    </div>
  );
};

// Styles
const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    backgroundColor: '#f5f5f5',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
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
  errorContainer: {
    textAlign: 'center',
    padding: '40px',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    border: '1px solid #ffcdd2',
  },
  errorTitle: {
    margin: '0 0 10px 0',
    color: '#d32f2f',
    fontSize: '24px',
  },
  errorMessage: {
    margin: '0 0 15px 0',
    color: '#666',
    fontSize: '16px',
  },
  redirectMessage: {
    margin: '0',
    color: '#999',
    fontSize: '14px',
  },
};

// Add CSS for spinner animation
const styleSheet = document.createElement("style");
styleSheet.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);

export default AuthCallback;