/**
 * OutputArea Component
 * Displays generated responses with copy functionality
 * Used on both LEFT and RIGHT sides
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './OutputArea.css';

function OutputArea({ response, intent, theme, loading, error, onRetry }) {
  const [copiedMessage, setCopiedMessage] = useState('');

  /**
   * Copy response to clipboard
   */
  const handleCopyToClipboard = async () => {
    if (!response) return;

    try {
      await navigator.clipboard.writeText(response);
      setCopiedMessage('Copied!');
      
      // Clear message after 2 seconds
      setTimeout(() => setCopiedMessage(''), 2000);
    } catch (err) {
      setCopiedMessage('Failed to copy');
      setTimeout(() => setCopiedMessage(''), 2000);
    }
  };

  /**
   * Render empty state
   */
  if (!response && !loading && !error) {
    return (
      <div className="output-area output-area-empty">
        <div className="empty-state">
          <div className="empty-icon">💬</div>
          <p className="empty-text">Response will appear here</p>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className="output-area output-area-error">
        <div className="error-container">
          <div className="error-title">❌ Error</div>
          <p className="error-text">{error}</p>
          {onRetry && (
            <button
              className="retry-button"
              onClick={onRetry}
              type="button"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    );
  }

  /**
   * Render loading state
   */
  if (loading) {
    return (
      <div className="output-area output-area-loading">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p className="loading-text">Generating response...</p>
        </div>
      </div>
    );
  }

  /**
   * Render response state
   */
  return (
    <div className="output-area output-area-response">
      <div className="response-container">
        {/* Response Text */}
        <div className="response-text-wrapper">
          <p className="response-text">{response}</p>
        </div>

        {/* Metadata - Intent (LEFT side) */}
        {intent && (
          <div className="intent-metadata">
            <div className="metadata-title">Detected Intent:</div>
            <div className="metadata-grid">
              <div className="metadata-item">
                <span className="metadata-label">Topic:</span>
                <span className="metadata-value">{intent.topic}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Tone:</span>
                <span className="metadata-value">{intent.tone}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Stage:</span>
                <span className="metadata-value">{intent.stage}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Energy:</span>
                <span className="metadata-value">{intent.energy}</span>
              </div>
            </div>
          </div>
        )}

        {/* Metadata - Theme (RIGHT side) */}
        {theme && !intent && (
          <div className="theme-metadata">
            <div className="metadata-title">Theme:</div>
            <div className="theme-badge">{theme}</div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="output-buttons">
          <button
            className={`copy-button ${copiedMessage ? 'copied' : ''}`}
            onClick={handleCopyToClipboard}
            disabled={!response}
            type="button"
            title="Copy response to clipboard"
          >
            <span className="copy-icon">
              {copiedMessage ? '✓' : '📋'}
            </span>
            <span className="copy-text">
              {copiedMessage || 'Copy'}
            </span>
          </button>

          <button
            className="select-button"
            onClick={() => {
              const selection = window.getSelection();
              const range = document.createRange();
              const responseText = document.querySelector('.response-text');
              if (responseText) {
                range.selectNodeContents(responseText);
                selection.removeAllRanges();
                selection.addRange(range);
              }
            }}
            type="button"
            title="Select all text"
          >
            <span className="select-icon">✓▢</span>
            <span className="select-text">Select</span>
          </button>
        </div>
      </div>
    </div>
  );
}

OutputArea.propTypes = {
  response: PropTypes.string,
  intent: PropTypes.shape({
    topic: PropTypes.string,
    tone: PropTypes.string,
    stage: PropTypes.string,
    energy: PropTypes.string,
  }),
  theme: PropTypes.string,
  loading: PropTypes.bool,
  error: PropTypes.string,
  onRetry: PropTypes.func,
};

OutputArea.defaultProps = {
  response: null,
  intent: null,
  theme: null,
  loading: false,
  error: null,
  onRetry: null,
};

export default OutputArea;
