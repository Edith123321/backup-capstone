// frontend_web/src/components/Auth/Login.jsx

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useLocation } from 'react-router-dom';
import './Auth.css';

const Login = () => {
  const { login } = useAuth();
  const location = useLocation();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const errorParam = params.get('error');

    if (errorParam) {
      setError(decodeURIComponent(errorParam));
    }
  }, [location]);

  const handleGoogleLogin = (e) => {
    e.preventDefault();

    setLoading(true);
    setError('');

    console.log("Redirecting to Google OAuth...");
    login();
  };

  return (
    <div className="auth-container">
      <div className="auth-grid">

        {/* LEFT SIDE */}
        <div className="auth-brand">
          <div className="auth-brand-content">

            <div className="auth-brand-icon">
              <svg width="56" height="56" viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="24" fill="#00464F"/>
                <path d="M24 12C17.373 12 12 17.373 12 24C12 30.627 17.373 36 24 36C30.627 36 36 30.627 36 24C36 17.373 30.627 12 24 12ZM24 33C19.029 33 15 28.971 15 24C15 19.029 19.029 15 24 15C28.971 15 33 19.029 33 24C33 28.971 28.971 33 24 33Z" fill="white"/>
                <path d="M24 18C21.2386 18 19 20.2386 19 23C19 25.7614 21.2386 28 24 28C26.7614 28 29 25.7614 29 23C29 20.2386 26.7614 18 24 18Z" fill="white"/>
                <path d="M30 26L33 30H27L30 26Z" fill="white"/>
                <path d="M18 26L15 30H21L18 26Z" fill="white"/>
              </svg>
            </div>

            <h1 className="auth-brand-title">Saka</h1>
            <p className="auth-brand-subtitle">
              AI-Powered RHD Detection
            </p>

            <div className="auth-brand-features">
              <div className="auth-brand-feature">
                <span className="auth-brand-check">
                  ✓
                </span>
                Early Detection
              </div>

              <div className="auth-brand-feature">
                <span className="auth-brand-check">
                  ✓
                </span>
                98.4% Accuracy
              </div>

              <div className="auth-brand-feature">
                <span className="auth-brand-check">
                  ✓
                </span>
                Non-Invasive
              </div>
            </div>

          </div>
        </div>

        {/* RIGHT SIDE */}
        <div className="auth-form-wrapper">

          <div className="auth-card">

            <div className="auth-header">
              <h2>Welcome Back</h2>
              <p>
                Sign in to access the Saka RHD Detection Dashboard
              </p>
            </div>

            {error && (
              <div className="auth-error">
                {error}
              </div>
            )}

            <button
              type="button"
              className="google-login-btn"
              onClick={handleGoogleLogin}
              disabled={loading}
            >
              <svg
                className="google-icon"
                viewBox="0 0 48 48"
                width="24"
                height="24"
              >
                <path
                  fill="#EA4335"
                  d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
                />
                <path
                  fill="#4285F4"
                  d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
                />
                <path
                  fill="#FBBC05"
                  d="M10.53 28.59A14.5 14.5 0 0 1 9.5 24c0-1.59.28-3.14.76-4.59l-7.98-6.19A23.99 23.99 0 0 0 0 24c0 3.77.87 7.35 2.56 10.56l7.97-5.97z"
                />
                <path
                  fill="#34A853"
                  d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 5.97C6.51 42.62 14.62 48 24 48z"
                />
              </svg>

              {loading ? "Redirecting to Google..." : "Continue with Google"}
            </button>

            <div className="auth-divider">
              <span className="divider-line"></span>
              <span className="divider-text">Secure Access</span>
              <span className="divider-line"></span>
            </div>

            <div className="auth-features">

              <div className="auth-feature">
                <span className="auth-feature-icon">🔒</span>
                <span>HIPAA Compliant</span>
              </div>

              <div className="auth-feature">
                <span className="auth-feature-icon">🛡️</span>
                <span>End-to-End Encrypted</span>
              </div>

              <div className="auth-feature">
                <span className="auth-feature-icon">👨‍⚕️</span>
                <span>For Healthcare Providers</span>
              </div>

            </div>

            <div className="auth-footer">
              <p>
                By continuing, you agree to our
                <a href="#"> Terms of Service</a>
                {" "}and{" "}
                <a href="#"> Privacy Policy</a>
              </p>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
};

export default Login;