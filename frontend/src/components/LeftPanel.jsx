/**
 * LeftPanel Component
 * Pasted conversation input with character count and Generate button
 * LEFT SIDE of split screen
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './LeftPanel.css';

function LeftPanel({ onGenerate, loading, onResponseReceived }) {
  const [conversation, setConversation] = useState('');
  const [charCount, setCharCount] = useState(0);
  const [error, setError] = useState('');

  const MAX_CHARS = 10000;
  const MIN_CHARS = 20;

  /**
   * Handle textarea input change
   */
  const handleConversationChange = (e) => {
    const text = e.target.value;
    setConversation(text);
    setCharCount(text.length);
    setError('');

    // Warn if too close to limit
    if (text.length > MAX_CHARS * 0.9) {
      setError(`Getting close to character limit (${text.length}/${MAX_CHARS})`);
    }
  };

  /**
   * Handle Generate button click
   */
  const handleGenerateClick = async () => {
    // Validate input
    if (!conversation.trim()) {
      setError('Please paste a conversation');
      return;
    }

    if (conversation.length < MIN_CHARS) {
      setError(`Conversation too short (${conversation.length}/${MIN_CHARS} characters minimum)`);
      return;
    }

    if (conversation.length > MAX_CHARS) {
      setError(`Conversation too long (${conversation.length}/${MAX_CHARS} characters maximum)`);
      return;
    }

    setError('');

    // Call parent callback
    try {
      await onGenerate(conversation);
    } catch (err) {
      setError(err.message || 'Failed to generate response');
    }
  };

  /**
   * Clear conversation
   */
  const handleClear = () => {
    setConversation('');
    setCharCount(0);
    setError('');
  };

  // Calculate progress percentage
  const progressPercent = (charCount / MAX_CHARS) * 100;

  return (
    <div className="left-panel">
      <div className="left-panel-container">
        <h2 className="left-panel-title">Paste Conversation</h2>
        
        <div className="textarea-wrapper">
          <textarea
            className="conversation-textarea"
            value={conversation}
            onChange={handleConversationChange}
            placeholder="Paste the last 10 messages from your conversation here..."
            disabled={loading}
            maxLength={MAX_CHARS}
          />
          
          {/* Character count and progress bar */}
          <div className="char-count-wrapper">
            <div className="char-count">
              {charCount} / {MAX_CHARS} characters
            </div>
            <div className="progress-bar-container">
              <div 
                className={`progress-bar ${progressPercent > 90 ? 'warning' : ''}`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Minimum characters indicator */}
        {charCount < MIN_CHARS && charCount > 0 && (
          <div className="info-message">
            <span className="info-icon">ℹ️</span>
            <span>Need {MIN_CHARS - charCount} more characters</span>
          </div>
        )}

        {/* Button group */}
        <div className="button-group">
          <button
            className={`generate-button ${loading ? 'loading' : ''}`}
            onClick={handleGenerateClick}
            disabled={loading || charCount < MIN_CHARS}
            type="button"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Generating...
              </>
            ) : (
              'Generate Response'
            )}
          </button>

          <button
            className="clear-button"
            onClick={handleClear}
            disabled={loading || charCount === 0}
            type="button"
            title="Clear textarea"
          >
            Clear
          </button>
        </div>

        {/* Instructions */}
        <div className="instructions">
          <p className="instruction-title">Instructions:</p>
          <ul>
            <li>Paste recent messages from your conversation</li>
            <li>Include both your messages and hers</li>
            <li>Minimum {MIN_CHARS} characters required</li>
            <li>Maximum {MAX_CHARS} characters allowed</li>
            <li>AI will analyze tone and generate contextual response</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

LeftPanel.propTypes = {
  onGenerate: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  onResponseReceived: PropTypes.func,
};

LeftPanel.defaultProps = {
  loading: false,
  onResponseReceived: null,
};

export default LeftPanel;
