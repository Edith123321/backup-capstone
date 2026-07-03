// frontend_web/src/components/Dashboard/Sidebar.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './DashboardLayout.css';

// Material Icons
import DashboardIcon from '@mui/icons-material/Dashboard';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import PeopleIcon from '@mui/icons-material/People';
import LibraryMusicIcon from '@mui/icons-material/LibraryMusic';
import DevicesIcon from '@mui/icons-material/Devices';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuIcon from '@mui/icons-material/Menu';
import CloseIcon from '@mui/icons-material/Close';
import PersonIcon from '@mui/icons-material/Person';

const Sidebar = ({ user }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
      if (window.innerWidth > 768) {
        setIsMobileOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const menuItems = [
    { id: 'dashboard', icon: DashboardIcon, label: 'Dashboard', path: '/dashboard' },
    { id: 'encounter', icon: PersonAddIcon, label: 'New Encounter', path: '/encounter/new' },
    { id: 'patients', icon: PeopleIcon, label: 'Patients', path: '/patients' },
    { id: 'recordings', icon: LibraryMusicIcon, label: 'Recordings', path: '/recordings' },
    { id: 'devices', icon: DevicesIcon, label: 'IoT Devices', path: '/devices' },
  ];

  const isActive = (path) => location.pathname === path;

  const handleNavigation = (path) => {
    navigate(path);
    if (isMobile) {
      setIsMobileOpen(false);
    }
  };

  const toggleSidebar = () => {
    if (isMobile) {
      setIsMobileOpen(!isMobileOpen);
    } else {
      setIsDesktopCollapsed(!isDesktopCollapsed);
    }
  };

  const isCollapsed = isMobile ? false : isDesktopCollapsed;

  return (
    <>
      {/* Mobile Overlay */}
      {isMobile && isMobileOpen && (
        <div className="sidebar-overlay" onClick={() => setIsMobileOpen(false)} />
      )}

      {/* Mobile Toggle Button */}
      {isMobile && (
        <button className="mobile-toggle" onClick={toggleSidebar}>
          {isMobileOpen ? <CloseIcon /> : <MenuIcon />}
        </button>
      )}

      <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''} ${isMobile ? 'mobile' : ''} ${isMobileOpen ? 'open' : ''}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="logo" onClick={() => handleNavigation('/dashboard')}>
            <span className="logo-icon"></span>
            {(!isCollapsed || isMobile) && <span className="logo-text">Saka</span>}
          </div>
          {!isMobile && (
            <button className="toggle-btn" onClick={toggleSidebar}>
              {isCollapsed ? '→' : '←'}
            </button>
          )}
        </div>

        {/* User Profile */}
        <div className="sidebar-user">
          {user?.picture ? (
            <img src={user.picture} alt={user.name} className="user-avatar" />
          ) : (
            <div className="user-avatar-placeholder">
              <PersonIcon />
            </div>
          )}
          {(!isCollapsed || isMobile) && (
            <div className="user-info">
              <span className="user-name">{user?.name || 'Doctor'}</span>
              <span className="user-email">{user?.email || ''}</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
                onClick={() => handleNavigation(item.path)}
              >
                <Icon className="nav-icon" />
                {(!isCollapsed || isMobile) && <span className="nav-label">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <button className="logout-btn" onClick={logout}>
            <LogoutIcon className="nav-icon" />
            {(!isCollapsed || isMobile) && <span className="nav-label">Logout</span>}
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;