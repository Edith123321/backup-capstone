// frontend_web/src/components/Common/LoadingSpinner.jsx
import React from 'react';
import './Common.css';

const LoadingSpinner = ({ message = 'Loading...', fullPage = true }) => {
  if (fullPage) {
    return (
      <div className="loading-fullpage">
        <div className="loading-content">
          <div className="spinner"></div>
          <p>{message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="loading-inline">
      <div className="spinner-small"></div>
      <span className="loading-text">{message}</span>
    </div>
  );
};

export default LoadingSpinner;