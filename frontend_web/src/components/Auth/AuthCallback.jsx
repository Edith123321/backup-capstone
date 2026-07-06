import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const processed = useRef(false); // Prevent double processing

  useEffect(() => {
    // Prevent double execution
    if (processed.current) {
      console.log('Already processed, skipping...');
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const userParam = params.get('user');

    console.log('AuthCallback - Token:', token ? 'Present' : 'Missing');
    console.log('AuthCallback - UserParam:', userParam ? 'Present' : 'Missing');

    if (!token || !userParam) {
      console.error('Missing auth data');
      setError('Missing authentication data');
      setLoading(false);
      
      // Redirect to login after 2 seconds
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);
      return;
    }

    try {
      // Mark as processed immediately to prevent double execution
      processed.current = true;
      
      // Decode the user parameter
      const decodedUser = decodeURIComponent(userParam);
      console.log('Decoded user string:', decodedUser);
      
      const user = JSON.parse(decodedUser);
      console.log('Parsed user object:', user);

      // Set authentication
      setAuth(token, user);
      setLoading(false);
      
      // Navigate to dashboard
      console.log('✅ Authentication successful, navigating to dashboard...');
      navigate('/dashboard', { replace: true });
      
    } catch (err) {
      console.error('Auth parse error:', err);
      setError('Failed to process authentication');
      setLoading(false);
      
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 3000);
    }
  }, [navigate, setAuth]);

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column'
      }}>
        <div>
          <h2>Completing login...</h2>
          <p>Please wait while we verify your credentials.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column'
      }}>
        <div style={{ textAlign: 'center', color: 'red' }}>
          <h2>Authentication Error</h2>
          <p>{error}</p>
          <p>Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return null;
};

export default AuthCallback;