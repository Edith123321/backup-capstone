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

    if (!token || !userParam) {
      setError('Missing authentication data');
      setTimeout(() => navigate('/login'), 2000);
      return;
    }

    try {
      // ✅ SAFE PARSE
      const decoded = decodeURIComponent(userParam);

      const user =
        typeof decoded === 'string'
          ? JSON.parse(decoded)
          : decoded;

      setAuth(token, user);

      navigate('/dashboard', { replace: true });

    } catch (err) {
      console.error('Auth parse error:', err);
      setError('Auth failed');
      setTimeout(() => navigate('/login'), 2000);
    }
  }, []);

  if (error) {
    return <div>{error}</div>;
  }

  return <div>Completing login...</div>;
};

export default AuthCallback;