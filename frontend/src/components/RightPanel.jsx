/**
 * RightPanel — the three "nothing to paste" scenario buttons:
 * New Match, Vulnerable, and Reply to Trigger. Each is a topic-tree generator,
 * so it never repeats. Everything conversation-driven lives in the left panel.
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { getAvailableButtons } from '../services/chatAPI';
import './RightPanel.css';

function RightPanel({ onButtonClick, loading, loadingButton, onOpenTimeModal }) {
  const [error, setError] = useState('');
  const buttons = getAvailableButtons();

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
        <div className="right-panel-header">
          <div className="right-panel-title-row">
            <h2 className="right-panel-title">Quick Scenarios</h2>
            <button
              type="button"
              className="update-time-btn"
              onClick={onOpenTimeModal}
              title="Change the time of day used for tone"
            >
              🕐 Update time
            </button>
          </div>
          <p className="right-panel-subtitle">No conversation to paste? Pick a scenario.</p>
        </div>

        <div className="cards-stack">
          {buttons.map((button) => (
            <button
              key={button.id}
              className={`scenario-card${loadingButton === button.id ? ' loading' : ''}`}
              onClick={() => handleButtonClick(button.id)}
              disabled={loading}
              type="button"
              aria-label={`${button.shortLabel} — ${button.description}`}
            >
              {loadingButton === button.id ? (
                <span className="card-spinner" aria-hidden="true" />
              ) : (
                <>
                  <span className="card-emoji" aria-hidden="true">{button.emoji}</span>
                  <span className="card-text">
                    <span className="card-label">{button.shortLabel}</span>
                    <span className="card-desc">{button.description}</span>
                  </span>
                  <span className="card-arrow" aria-hidden="true">→</span>
                </>
              )}
            </button>
          ))}
        </div>

        {error && (
          <div className="error-message" role="alert">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}

RightPanel.propTypes = {
  onButtonClick: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  loadingButton: PropTypes.string,
  onOpenTimeModal: PropTypes.func,
};

RightPanel.defaultProps = {
  loading: false,
  loadingButton: null,
  onOpenTimeModal: () => {},
};

export default RightPanel;
