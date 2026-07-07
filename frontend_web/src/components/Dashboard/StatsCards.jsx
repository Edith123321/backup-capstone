// frontend_web/src/components/Dashboard/StatsCards.jsx
import React from 'react';
import './DashboardLayout.css';

const StatsCards = ({ stats }) => {
  const cards = [
    {
      title: 'Total Patients',
      value: stats.totalPatients || 0,
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
      change: '+0%',
      color: '#3b82f6'
    },
    {
      title: "Today's Screenings",
      value: stats.todayScreenings || 0,
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
      change: '+0',
      color: '#0D9488'
    },
    {
      title: 'Total Recordings',
      value: stats.totalRecordings || 0,
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="5 3 19 12 5 21 5 3" />
          <path d="M12 12l-4 2.5" />
          <path d="M12 12l4 2.5" />
        </svg>
      ),
      change: '+0',
      color: '#8b5cf6'
    },
    {
      title: 'Flagged for Review',
      value: stats.flagged || 0,
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M12 8v4" />
          <path d="M12 16h.01" />
        </svg>
      ),
      change: '+0',
      color: '#ef4444'
    }
  ];

  return (
    <div className="stats-cards">
      {cards.map((card, index) => (
        <div key={index} className="stat-card">
          <div className="stat-card-icon" style={{ color: card.color }}>
            {card.icon}
          </div>
          <div className="stat-card-content">
            <div className="stat-card-value">{card.value}</div>
            <div className="stat-card-title">{card.title}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;