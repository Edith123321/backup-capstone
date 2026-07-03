// frontend_web/src/components/Landing/CTASection.js
import React from 'react';
import './LandingPage.css';

const CTASection = ({ onGetStarted }) => {
  return (
    <section className="cta-section">
      <div className="container">
        <div className="cta-wrapper">
          <div className="cta-content">
            <h2>Protect Africa's Future Leaders</h2>
            <p className="cta-description">
              Every child deserves a healthy heart. Join healthcare providers, 
              community health workers, and organizations across Africa who are 
              using Saka to detect RHD early and save lives.
            </p>
            
            <div className="cta-stats">
              <div className="cta-stat-item">
            
              </div>
            </div>
            
            <div className="cta-actions">
              <button className="btn-primary" onClick={onGetStarted}>
                Get Started Now
                <span className="btn-icon">→</span>
              </button>
              <button className="btn-secondary">
                Learn More
              </button>
            </div>
            
            {/* <div className="cta-features">
              <div className="cta-feature-item">
                <span className="cta-feature-icon">✓</span>
                Free for healthcare providers
              </div>
              <div className="cta-feature-item">
                <span className="cta-feature-icon">✓</span>
                GDPR & HIPAA Compliant
              </div>
              <div className="cta-feature-item">
                <span className="cta-feature-icon">✓</span>
                Available worldwide
              </div>
              <div className="cta-feature-item">
                <span className="cta-feature-icon">✓</span>
                Non-invasive screening
              </div>
            </div> */}
          </div>
          
          <div className="cta-visual">
            {/* <div className="cta-card">
              <div className="cta-card-header">
                <div className="cta-card-pulse">
                  <div className="cta-pulse-ring"></div>
                  <div className="cta-pulse-ring"></div>
                  <div className="cta-pulse-ring"></div>
                  <div className="cta-heart-icon">❤</div>
                </div>
                <div className="cta-card-title">
                  <h4>Saka AI Screening</h4>
                  <span className="cta-card-status">Active</span>
                </div>
              </div>
              <div className="cta-card-body">
                <div className="cta-card-row">
                  <span className="cta-card-label">Today's Screenings</span>
                  <span className="cta-card-value">47</span>
                </div>
                <div className="cta-card-row">
                  <span className="cta-card-label">Detection Rate</span>
                  <span className="cta-card-value">98.4%</span>
                </div>
                <div className="cta-card-progress">
                  <div className="cta-progress-bar">
                    <div className="cta-progress-fill" style={{ width: '85%' }}></div>
                  </div>
                  <span className="cta-progress-label">85% Early Detection</span>
                </div>
              </div>
              <div className="cta-card-footer">
                <span>Join 500+ healthcare providers</span>
              </div>
            </div> */}
          </div>
        </div>
      </div>
    </section>
  );
};

export default CTASection;