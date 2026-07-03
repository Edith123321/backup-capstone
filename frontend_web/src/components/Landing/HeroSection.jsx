// frontend_web/src/components/Landing/HeroSection.js
import React from 'react';
import './LandingPage.css';
import landingPageImage from './LandingPage.jpg'; // Import the image directly

const HeroSection = ({ onGetStarted }) => {
  return (
    <section className="hero-section">
      <div className="hero-background">
        <img 
          src={landingPageImage} 
          alt="African children playing" 
          className="hero-bg-image"
        />
        <div className="hero-gradient-overlay"></div>
      </div>
      <div className="container">
        <div className="hero-content">
          <div className="hero-text">
            <h1 className="hero-title">
              Guarding the hearts of Africa's Future
            </h1>
            <p className="hero-description">
              Saka uses AI technology and IoT for Early detection of Rheumatic Heart Disease (RHD) using advanced. 
              The technology offers a cheaper alternative to Echocardiograms for RHD detection.
            </p>
            <div className="hero-actions">
              <button className="btn-primary" onClick={onGetStarted}>
                Get Started
                <span className="btn-icon">→</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;