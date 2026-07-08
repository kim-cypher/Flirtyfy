/**
 * RightPanel — 36 scenario buttons in a 6×6 grid.
 * Ordered: Opening → Emotional → Daily → Fantasy → Personal → Sexual
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { getAvailableButtons } from '../services/chatAPI';
import './RightPanel.css';

function RightPanel({ onButtonClick, loading, loadingButton, onOpenTimeModal }) {
  const [error, setError] = useState('');
  const allButtons = getAvailableButtons();
  const mainButtons  = allButtons.filter(b => b.row < 7);
  const extraButtons = allButtons.filter(b => b.row === 7);

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
          <p className="right-panel-subtitle">Stuck? Insisting to meet? Click the buttons. Happy Flirting!</p>
        </div>

        <div className="buttons-grid">
          {mainButtons.map((button) => (
            <button
              key={button.id}
              className={`scenario-button${loadingButton === button.id ? ' loading' : ''}`}
              onClick={() => handleButtonClick(button.id)}
              disabled={loading}
              type="button"
              title={button.description}
              aria-label={`${button.shortLabel} — ${button.description}`}
            >
              <span className="button-label">{button.shortLabel}</span>
              {loadingButton === button.id && (
                <span className="button-spinner" aria-hidden="true" />
              )}
            </button>
          ))}
        </div>

        {extraButtons.length > 0 && (
          <>
            <div className="buttons-section-divider">
              <span>Get to Know Him</span>
            </div>
            <div className="buttons-grid">
              {extraButtons.map((button) => (
                <button
                  key={button.id}
                  className={`scenario-button${loadingButton === button.id ? ' loading' : ''}`}
                  onClick={() => handleButtonClick(button.id)}
                  disabled={loading}
                  type="button"
                  title={button.description}
                  aria-label={`${button.shortLabel} — ${button.description}`}
                >
                  <span className="button-label">{button.shortLabel}</span>
                  {loadingButton === button.id && (
                    <span className="button-spinner" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          </>
        )}

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
