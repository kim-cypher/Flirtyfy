import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './OutputArea.css';

function OutputArea({ response, loading, error }) {
  const [copied, setCopied] = useState(false);

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
      </div>
    </div>
  );
}

OutputArea.propTypes = {
  response: PropTypes.string,
  loading: PropTypes.bool,
  error: PropTypes.string,
};

OutputArea.defaultProps = {
  response: null,
  loading: false,
  error: null,
};

export default OutputArea;
