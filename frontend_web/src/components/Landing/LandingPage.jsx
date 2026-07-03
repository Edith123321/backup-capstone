// frontend_web/src/components/Landing/LandingPage.js
import React from 'react';
import { useNavigate } from 'react-router-dom';
import HeroSection from './HeroSection';
import FeaturesSection from './FeaturesSection';
import StatsSection from './StatsSection';
import CTASection from './CTASection';
import Navbar from '../Common/Navbar';
import Footer from '../Common/Footer';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/login');
  };

  return (
    <div className="landing-page">
      <Navbar isLanding={true} />
      <main>
        <HeroSection onGetStarted={handleGetStarted} />
        <StatsSection />
        <FeaturesSection />
        <CTASection onGetStarted={handleGetStarted} />
      </main>
      <Footer isLanding={true} />
    </div>
  );
};

export default LandingPage;