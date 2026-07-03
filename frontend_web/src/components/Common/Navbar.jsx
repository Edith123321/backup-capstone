// frontend_web/src/components/Common/Navbar.js
import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Common.css';

const Navbar = ({ isLanding = false }) => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const closeMenu = () => {
    setIsOpen(false);
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <nav className={`navbar ${isLanding ? 'navbar-landing' : ''} ${scrolled ? 'navbar-scrolled' : ''}`}>
      <div className="navbar-container">
        <Link to="/" className="navbar-logo" onClick={closeMenu}>
          <svg className="navbar-logo-icon" width="32" height="32" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="24" fill="#00464F"/>
            <path d="M24 12C17.373 12 12 17.373 12 24C12 30.627 17.373 36 24 36C30.627 36 36 30.627 36 24C36 17.373 30.627 12 24 12ZM24 33C19.029 33 15 28.971 15 24C15 19.029 19.029 15 24 15C28.971 15 33 19.029 33 24C33 28.971 28.971 33 24 33Z" fill="white"/>
            <path d="M24 18C21.2386 18 19 20.2386 19 23C19 25.7614 21.2386 28 24 28C26.7614 28 29 25.7614 29 23C29 20.2386 26.7614 18 24 18Z" fill="white"/>
          </svg>
          <span className="logo-text">Saka</span>
        </Link>

        <button 
          className="navbar-toggle" 
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle navigation menu"
        >
          <span className={`toggle-bar ${isOpen ? 'active' : ''}`}></span>
          <span className={`toggle-bar ${isOpen ? 'active' : ''}`}></span>
          <span className={`toggle-bar ${isOpen ? 'active' : ''}`}></span>
        </button>

        <div className={`navbar-menu ${isOpen ? 'active' : ''}`}>
          {!isLanding && isAuthenticated && (
            <>
              <Link 
                to="/dashboard" 
                className={`navbar-link ${isActive('/dashboard') ? 'active' : ''}`}
                onClick={closeMenu}
              >
                <svg className="nav-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7"/>
                  <rect x="14" y="3" width="7" height="7"/>
                  <rect x="3" y="14" width="7" height="7"/>
                  <rect x="14" y="14" width="7" height="7"/>
                </svg>
                Dashboard
              </Link>
              <Link 
                to="/history" 
                className={`navbar-link ${isActive('/history') ? 'active' : ''}`}
                onClick={closeMenu}
              >
                <svg className="nav-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                History
              </Link>
            </>
          )}
          
          {isAuthenticated ? (
            <div className="navbar-user">
              <div className="user-info">
                {user?.picture ? (
                  <img src={user.picture} alt="Profile" className="user-avatar" />
                ) : (
                  <div className="user-avatar-placeholder">
                    {user?.name?.charAt(0) || 'U'}
                  </div>
                )}
                <span className="user-name">{user?.name?.split(' ')[0] || 'User'}</span>
              </div>
              <button className="navbar-logout" onClick={handleLogout}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                Logout
              </button>
            </div>
          ) : (
            <Link to="/login" className="navbar-btn" onClick={closeMenu}>
              Sign In
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                <polyline points="10 17 15 12 10 7"/>
                <line x1="15" y1="12" x2="3" y2="12"/>
              </svg>
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;