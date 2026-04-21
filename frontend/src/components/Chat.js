/**
 * Chat Component - Simplified Design
 * 3 Main Elements: Input, Generate Button, Reply Output
 * Dark Purple Theme
 */

import React, { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import { uploadChat, fetchLatestReply } from '../services/chatService';
import './Chat.css';

function Chat() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);

  const [conversation, setConversation] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const pollIntervalRef = useRef(null);
  const timeoutRef = useRef(null);

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const handleGoHome = () => {
    navigate('/dashboard');
  };

  const handleGoToLocations = () => {
    navigate('/locations');
  };

  const handleGenerateResponse = async () => {
    if (!conversation.trim()) {
      setError('Please paste a conversation');
      return;
    }

    setLoading(true);
    setError('');
    setResponse('');
    setProcessing(false);

    try {
      const result = await uploadChat(conversation);

      if (result && result.id) {
        setProcessing(true);
        setLoading(false);

        const pollFunction = async () => {
          try {
            const latestReply = await fetchLatestReply();

            if (latestReply && latestReply.length > 0) {
              const latest = latestReply[0];
              if ((latest.status === 'complete' || latest.status === 'completed') && latest.original_text) {
                setResponse(latest.original_text);
                setProcessing(false);
                if (pollIntervalRef.current) {
                  clearInterval(pollIntervalRef.current);
                  pollIntervalRef.current = null;
                }
              }
            }
          } catch (pollError) {
            console.error('Polling error:', pollError);
          }
        };

        const newPollInterval = setInterval(pollFunction, 2000);
        pollIntervalRef.current = newPollInterval;

        timeoutRef.current = setTimeout(() => {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            setError('Request timeout - please try again');
            setProcessing(false);
          }
        }, 60000);
      }
    } catch (err) {
      setError(err.message || 'Failed to upload conversation');
      setLoading(false);
    }
  };

  const handleCopyResponse = () => {
    if (response) {
      navigator.clipboard.writeText(response);
    }
  };

  const handleNext = () => {
    setResponse('');
    setError('');
    setConversation('');
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <h1>Let's Chat!</h1>
        </div>
        <div className="header-right">
          <button className="btn-nav" onClick={handleGoHome}>
            Home
          </button>
          <button className="btn-nav" onClick={handleGoToLocations}>
            Find Locations
          </button>
          {user && <span className="user-name">{user.username}</span>}
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      {/* Main Content - 3 Elements */}
      <div className="chat-main">
        {/* 1. Input Area */}
        <textarea
          className="input-area"
          placeholder="Paste your conversations here..."
          value={conversation}
          onChange={(e) => setConversation(e.target.value)}
          disabled={loading || processing}
        />

        {/* 2. Generate Button */}
        <button
          className={`btn-generate ${loading || processing ? 'loading' : ''}`}
          onClick={handleGenerateResponse}
          disabled={loading || processing || !conversation.trim()}
        >
          {loading ? 'Uploading...' : processing ? 'Generating...' : 'Generate'}
        </button>

        {/* 3. Reply Output */}
        <div className="reply-section">
          <label className="reply-label">Generated Reply</label>
          <div className="output-area">
            {error && <div className="error-message">{error}</div>}
            {processing && !response && (
              <div className="processing-message">Waiting for AI reply...</div>
            )}
            {response && (
              <div className="reply-content">
                <div className="reply-text">{response}</div>
                <div className="reply-actions">
                  <button className="btn-copy" onClick={handleCopyResponse}>
                    Copy
                  </button>
                  <button className="btn-next" onClick={handleNext}>
                    Next
                  </button>
                </div>
              </div>
            )}
            {!response && !processing && !error && (
              <div className="placeholder-text">Your reply will appear here</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat;
