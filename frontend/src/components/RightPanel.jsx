/**
 * RightPanel Component
 * 13 scenario buttons for quick response generation
 * RIGHT SIDE of split screen
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { getAvailableButtons } from '../services/chatAPI';
import './RightPanel.css';

function RightPanel({ onButtonClick, loading, loadingButton }) {
  const [error, setError] = useState('');
  const buttons = getAvailableButtons();

  /**
   * Handle button click
   */
  const handleButtonClick = async (buttonId) => {
    setError('');
    try {
      await onButtonClick(buttonId);
    } catch (err) {
      setError(err.message || 'Failed to generate response');
    }
  };

  return (
    <div className="right-panel">
      <div className="right-panel-container">
        <h2 className="right-panel-title">Quick Scenarios</h2>
        
        <div className="buttons-grid">
          {buttons.map((button) => (
            <button
              key={button.id}
              className={`scenario-button ${loadingButton === button.id ? 'loading' : ''}`}
              onClick={() => handleButtonClick(button.id)}
              disabled={loading}
              type="button"
              title={button.description}
              aria-label={`${button.label} - ${button.description}`}
            >
              <span className="button-label">{button.label}</span>
              
              {loadingButton === button.id && (
                <span className="button-spinner"></span>
              )}
            </button>
          ))}
        </div>

        {/* Error message */}
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Instructions */}
        <div className="button-instructions">
          <p className="instruction-title">How to Use:</p>
          <ul>
            <li>Click any button to generate a response</li>
            <li>Each button uses a different scenario</li>
            <li>AI generates unique responses each time</li>
            <li>Same theme won't repeat within 24 hours</li>
            <li>Perfect for starting conversations</li>
          </ul>
        </div>

        {/* Legend */}
        <div className="button-legend">
          <p className="legend-title">Button Guide:</p>
          <div className="legend-grid">
            {buttons.slice(0, 4).map((button) => (
              <div key={button.id} className="legend-item">
                <span className="legend-label">{button.label}</span>
                <span className="legend-desc">{button.description}</span>
              </div>
            ))}
          </div>
          <button 
            className="expand-legend-button"
            onClick={() => {
              const legend = document.querySelector('.full-legend');
              legend.classList.toggle('visible');
            }}
            type="button"
          >
            View All Descriptions
          </button>
          
          <div className="full-legend">
            {buttons.map((button) => (
              <div key={button.id} className="legend-item-full">
                <strong>{button.label}:</strong> {button.description}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

RightPanel.propTypes = {
  onButtonClick: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  loadingButton: PropTypes.string,
};

RightPanel.defaultProps = {
  loading: false,
  loadingButton: null,
};

export default RightPanel;
