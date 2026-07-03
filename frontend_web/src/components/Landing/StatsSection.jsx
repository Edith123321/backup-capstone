// frontend_web/src/components/Landing/StatsSection.js
import React from 'react';
import './LandingPage.css';

const StatsSection = () => {
  const stats = [
    {
      number: '14',
      label: 'Countries Active',
      description: 'Reaching communities across Africa'
    },
    {
      number: '5k+',
      label: 'Screenings Performed',
      description: 'And growing every day'
    },
    {
      number: '98.4%',
      label: 'Detection Accuracy',
      description: 'Validated by clinical studies'
    },
    {
      number: '10',
      label: 'Minutes to Result',
      description: 'From upload to diagnosis'
    }
  ];

  return (
    <section className="stats-section">
      <div className="container">
        <div className="stats-grid">
          
        </div>
      </div>
    </section>
  );
};

export default StatsSection;