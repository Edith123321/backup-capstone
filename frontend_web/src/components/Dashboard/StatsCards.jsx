// frontend_web/src/components/Dashboard/StatsCards.jsx
import React from 'react';
import './DashboardLayout.css';

const StatsCards = ({ stats }) => {
  const cards = [
    {
      title: 'Total Patients',
      value: stats.totalPatients || 0,
      icon: '',
      change: '+0%'
    },
    {
      title: "Today's Screenings",
      value: stats.todayScreenings || 0,
      icon: '',
      change: '+0'
    },
    {
      title: 'Total Recordings',
      value: stats.totalRecordings || 0,
      icon: '',
      change: '+0'
    },
    {
      title: 'Flagged for Review',
      value: stats.flagged || 0,
      icon: '',
      change: '+0'
    }
  ];

  return (
    <div className="stats-cards">
      {cards.map((card, index) => (
        <div key={index} className="stat-card">
          <div className="stat-card">{card.icon}</div>
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