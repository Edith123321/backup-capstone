import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Auth.css';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { handleAuthCallback } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('🔄 AuthCallback component mounted');
    
    // Get the full URL
    const fullUrl = window.location.href;
    console.log('📍 Full URL:', fullUrl);
    
    // Parse URL parameters
    const params = new URLSearchParams(window.location.search);
    
    // Get token and user data
    const token = params.get('token');
    const userDataParam = params.get('user');
    
    console.log('🔑 Token found:', !!token);
    console.log('👤 User data param found:', !!userDataParam);
    
    if (token && userDataParam) {
      try {
        // Decode the user data (it's URL encoded)
        const userData = decodeURIComponent(userDataParam);
        console.log('📝 Decoded user data string:', userData);
        
        // Parse the JSON
        const user = JSON.parse(userData);
        console.log('✅ Parsed user object:', user);
        
        // Save to localStorage
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
        console.log('💾 Saved to localStorage');
        
        // Update auth context
        handleAuthCallback(token, user);
        console.log('🔄 Auth context updated');
        
        // Redirect to dashboard
        console.log('🚀 Redirecting to dashboard...');
        navigate('/dashboard');
        
      } catch (error) {
        console.error('❌ Error processing auth data:', error);
        console.error('Raw user data:', userDataParam);
        setError(`Failed to process authentication: ${error.message}`);
      }
    } else {
      console.error('❌ Missing token or user data');
      console.log('Token:', token);
      console.log('User data param:', userDataParam);
      setError('No authentication token received. Please try again.');
      
      // If there's an error parameter, show it
      const errorParam = params.get('error');
      if (errorParam) {
        setError(decodeURIComponent(errorParam));
      }
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    }
  }, [handleAuthCallback, navigate]);

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