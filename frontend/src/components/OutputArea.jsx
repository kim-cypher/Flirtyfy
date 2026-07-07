import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { sendReplyFeedback } from '../services/chatAPI';
import './OutputArea.css';

const RATINGS = [
  { value: 'excellent', label: 'Excellent' },
  { value: 'good', label: 'Good' },
  { value: 'bad', label: 'Bad' },
];

function OutputArea({ response, replyId, loading, error }) {
  const [copied, setCopied] = useState(false);
  const [rated, setRated] = useState('');

  // New reply → fresh rating state
  useEffect(() => {
    setRated('');
    setCopied(false);
  }, [replyId, response]);

  const handleCopy = async () => {
    if (!response) return;
    try {
      await navigator.clipboard.writeText(response);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const handleRate = async (value) => {
    if (rated || !replyId) return;
    setRated(value); // optimistic — the user's click always "works"
    try {
      await sendReplyFeedback(replyId, value);
    } catch {
      /* non-fatal: rating UI already acknowledged */
    }
  };

  if (loading) {
    return (
      <div className="output-area output-loading">
        <span className="output-spinner" />
        <p className="output-loading-text">Writing your reply…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="output-area output-error">
        <p className="output-error-text">{error}</p>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="output-area output-empty">
        <p className="output-empty-text">Your reply will appear here</p>
      </div>
    );
  }

  return (
    <div className="output-area output-ready">
      <p className="output-reply-text">{response}</p>
      <div className="output-footer">
        <button
          className={`btn-copy ${copied ? 'copied' : ''}`}
          onClick={handleCopy}
          type="button"
        >
          {copied ? 'Copied!' : 'Copy to chat'}
        </button>
        {replyId && (
          <div className="output-rating" aria-label="Rate this reply">
            {rated ? (
              <span className="rating-thanks">Thanks for the feedback!</span>
            ) : (
              <>
                <span className="rating-label">Rate:</span>
                {RATINGS.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    className={`rating-btn rating-${r.value}`}
                    onClick={() => handleRate(r.value)}
                  >
                    {r.label}
                  </button>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

OutputArea.propTypes = {
  response: PropTypes.string,
  replyId: PropTypes.number,
  loading: PropTypes.bool,
  error: PropTypes.string,
};

OutputArea.defaultProps = {
  response: null,
  replyId: null,
  loading: false,
  error: null,
};

export default OutputArea;
