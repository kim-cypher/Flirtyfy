import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './LeftPanel.css';

const MAX_CHARS = 10000;
const MIN_CHARS = 20;

function LeftPanel({ onGenerate, loading }) {
  const [conversation, setConversation] = useState('');
  const [error, setError] = useState('');
  const [hisLastN, setHisLastN] = useState(1);

  const charCount = conversation.length;
  const progressPercent = Math.min((charCount / MAX_CHARS) * 100, 100);

  const handleChange = (e) => {
    setConversation(e.target.value);
    setError('');
  };

  const handleGenerate = async () => {
    if (!conversation.trim()) { setError('Paste a conversation first.'); return; }
    if (charCount < MIN_CHARS) { setError(`Need ${MIN_CHARS - charCount} more characters.`); return; }
    if (charCount > MAX_CHARS) { setError('Too long — max 10,000 characters.'); return; }
    setError('');
    try {
      await onGenerate(conversation, hisLastN);
    } catch (err) {
      setError(err.message || 'Failed to generate reply.');
    }
  };

  const handleClear = () => {
    setConversation('');
    setError('');
    setHisLastN(1);
  };

  return (
    <div className="left-panel">
      <h2 className="panel-title">Paste &amp; Reply</h2>

      <div className="textarea-block">
        <textarea
          className="conversation-textarea"
          value={conversation}
          onChange={handleChange}
          placeholder="Paste the last three conversations here…"
          disabled={loading}
          maxLength={MAX_CHARS}
        />
        <div className="char-row">
          <div className="char-count">{charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}</div>
          <div className="progress-track">
            <div
              className={`progress-fill ${progressPercent > 90 ? 'warning' : ''}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="inline-error">{error}</div>
      )}

      {charCount > 0 && charCount < MIN_CHARS && (
        <div className="inline-hint">Need {MIN_CHARS - charCount} more characters</div>
      )}

      <div className="his-last-n" title="How many of the last messages are HIS? Bump this up when he sent several in a row.">
        <span className="his-last-n-label">His last messages</span>
        <div className="his-last-n-steps">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              className={`his-last-n-step${hisLastN === n ? ' active' : ''}`}
              onClick={() => setHisLastN(n)}
              disabled={loading}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      <div className="action-row">
        <button
          className={`btn-generate ${loading ? 'loading' : ''}`}
          onClick={handleGenerate}
          disabled={loading || charCount < MIN_CHARS}
          type="button"
        >
          {loading ? (
            <><span className="btn-spinner" /> Generating…</>
          ) : (
            'Generate Reply'
          )}
        </button>
        <button
          className="btn-clear"
          onClick={handleClear}
          disabled={loading || charCount === 0}
          type="button"
        >
          Clear
        </button>
      </div>
    </div>
  );
}

LeftPanel.propTypes = {
  onGenerate: PropTypes.func.isRequired,
  loading: PropTypes.bool,
};

LeftPanel.defaultProps = {
  loading: false,
};

export default LeftPanel;
