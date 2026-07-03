// frontend_web/src/components/Landing/FeaturesSection.js
import React from 'react';
import './LandingPage.css';
import prevalenceImage from './prevalence.jpg';

const FeaturesSection = () => {
  const features = [
    {
      title: 'Non-Invasive Screening',
      description: 'Digital screening that identifies early signals without invasive procedures, making it safe and accessible for children across Africa.'
    },
    {

      title: 'Mobile-First Technology',
      description: 'Designed for use in remote and resource-limited settings, bringing cardiac screening to underserved communities.'
    },
    {
     
      title: 'AI-Powered Analysis',
      description: 'Advanced artificial intelligence algorithms analyze heart sounds with high accuracy, detecting subtle abnormalities early.'
    },
    {
  
      title: 'Clinical Integration',
      description: 'Seamlessly integrates with existing healthcare systems, providing actionable insights for healthcare providers.'
    }
  ];

  const statistics = [
    {
      number: '98.4%',
      label: 'Detection Accuracy'
    },
    {
      number: '10+',
      label: 'Children Screened'
    },

    {
      number: '85%',
      label: 'Early Detection Rate'
    }
  ];

  return (
    <section className="features-section">
      <div className="container">
        {/* Mission Section */}
        <div className="mission-section">
          <div className="mission-header">
            <span className="section-badge">Our Mission</span>
          </div>
          <div className="mission-content">
            <div className="mission-image-wrapper">
              <img 
                src={prevalenceImage} 
                alt="Rheumatic Heart Disease prevalence in Africa" 
                className="mission-image"
              />
            </div>
            <div className="mission-text-wrapper">
              <h2 className="mission-title">Saka's Mission</h2>
              <p className="mission-description">
  Every child deserves the opportunity to grow up with a healthy heart. Yet Rheumatic Heart Disease (RHD) continues to affect millions of children and young adults, particularly in low-resource communities where access to early screening is limited. What often begins as a common, treatable sore throat caused by a bacterial infection can silently progress into permanent damage to the heart valves if left undiagnosed and untreated.
</p>

{/* <p className="mission-description">
  Saka is committed to changing this reality through fast, non-invasive digital screening that helps identify early signs of Rheumatic Heart Disease before severe complications develop. By combining accessible technology with intelligent analysis, we empower healthcare providers to make timely, informed decisions, expand access to preventive care, and improve health outcomes for children and communities across Africa.
</p> */}
              
              {/* Statistics */}
              <div className="statistics-grid">
                {statistics.map((stat, index) => (
                  <div key={index} className="stat-item">
                    <span className="stat-number">{stat.number}</span>
                    <span className="stat-label">{stat.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="features-header">
          <span className="section-badge">How Saka Works</span>
          <h2></h2>
          <p className="section-description">
            Advanced technology designed to detect RHD early and save young lives across Africa
          </p>
        </div>
        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeaturesSection;