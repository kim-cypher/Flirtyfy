/**
 * Chat Component
 * 
 * Main landing page after user login
 * Allows users to paste conversations and get AI-generated replies
 * Features:
 * - Paste conversation (last 10 texts)
 * - Generate human-like AI response
 * - View response uniqueness status
 * - Copy response to clipboard
 * - Upload another conversation (next feature)
 * - No database storage - session only
 */

import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import { uploadChat, fetchLatestReply } from '../services/chatService';
import './Chat.css';

function Chat() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);

  // State management
  const [conversation, setConversation] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const [isUnique, setIsUnique] = useState(null);
  const [jobStatus, setJobStatus] = useState('');
  const [copied, setCopied] = useState(false);
  const [responseHistory, setResponseHistory] = useState([]);
  const [pollInterval, setPollInterval] = useState(null);

  /**
   * Handle logout
   */
  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  /**
   * Navigate to Dashboard
   */
  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  /**
   * Navigate to Find Location
   */
  const handleGoToLocations = () => {
    navigate('/locations');
  };

  /**
   * Generate AI response to the pasted conversation
   */
  // Handle chat upload and start polling for reply
  const handleGenerateResponse = async () => {
    if (!conversation.trim()) {
      setError('Please paste a conversation first');
      return;
    }
    if (conversation.trim().length < 10) {
      setError('Please paste a longer conversation (at least 10 characters)');
      return;
    }
    setLoading(true);
    setError('');
    setResponse('');
    setIsUnique(null);
    setJobStatus('');
    setProcessing(false);
    try {
      // Upload chat to backend
      await uploadChat(conversation);
      setProcessing(true);
      setLoading(false);
      setJobStatus('pending');
      // Start polling for reply
      const interval = setInterval(async () => {
        try {
          const replyData = await fetchLatestReply();
          if (replyData && replyData.length > 0) {
            const latest = replyData[0];
            setJobStatus(latest.status || '');
            if (latest.status === 'complete' && latest.reply) {
              setResponse(latest.reply);
              setIsUnique(latest.is_unique);
              setProcessing(false);
              setJobStatus('complete');
              setResponseHistory([
                ...responseHistory,
                {
                  conversation: conversation,
                  response: latest.reply,
                  isUnique: latest.is_unique,
                  timestamp: new Date().toLocaleTimeString(),
                },
              ]);
              setConversation('');
              clearInterval(interval);
              setPollInterval(null);
            } else if (latest.status === 'fallback' && latest.reply) {
              setResponse(latest.reply);
              setIsUnique(latest.is_unique);
              setProcessing(false);
              setJobStatus('fallback');
              setResponseHistory([
                ...responseHistory,
                {
                  conversation: conversation,
                  response: latest.reply,
                  isUnique: latest.is_unique,
                  timestamp: new Date().toLocaleTimeString(),
                },
              ]);
              setConversation('');
              clearInterval(interval);
              setPollInterval(null);
            }
          }
        } catch (err) {
          setError('Error polling for reply.');
          setProcessing(false);
          clearInterval(interval);
          setPollInterval(null);
        }
      }, 2000); // Poll every 2 seconds
      setPollInterval(interval);
    } catch (err) {
      setError(err.message || 'Error: Could not connect to the server.');
      setLoading(false);
      setProcessing(false);
    }
  };

  /**
   * Copy response to clipboard
   */
  const handleCopyResponse = () => {
    if (!response) return;

    navigator.clipboard.writeText(response).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000); // Reset after 2 seconds
    });
  };

  /**
   * Handle "Next" button - clear response and load next conversation
   */
  const handleNext = () => {
    setResponse('');
    setIsUnique(null);
    setError('');
    setJobStatus('');
    setProcessing(false);
    if (pollInterval) {
      clearInterval(pollInterval);
      setPollInterval(null);
    }
    // Focus on textarea so user can immediately paste next conversation
    document.getElementById('conversationInput').focus();
  };

  return (
    <div className="chat-container">
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="nav-left">
          <h2>💬 Flirty Chat</h2>
        </div>
        <div className="nav-center">
          <button className="nav-btn active">Chat</button>
          <button className="nav-btn" onClick={handleGoToLocations}>
            📍 Find Location
          </button>
          <button className="nav-btn" onClick={handleGoToDashboard}>
            ⚙️ Profile
          </button>
        </div>
        <div className="nav-right">
          <span className="user-info">Welcome, {user?.username}!</span>
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className="chat-content">
        <div className="chat-header">
          <h1>Generate Natural Replies</h1>
          <p>Paste a conversation, get a unique AI response from a different woman each time</p>
          <div className="chat-info-banner">
            <span className="info-icon">💡</span>
            <span className="info-text">
              Each response comes from a fresh female persona that matches the conversation tone. Every interaction is with someone new!
            </span>
          </div>
        </div>

        <div className="chat-main">
          {/* Left Column - Input */}
          <div className="chat-section input-section">
            <h3>📝 Paste Conversation</h3>
            <p className="section-description">
              Paste the last texts from a conversation and receive unique responses. 
            </p>

            <textarea
              id="conversationInput"
              className="conversation-input"
              placeholder="Paste the last 10 texts from a conversation here...&#10;&#10;Example:&#10;Person A: Hey, how are you?&#10;Person B: Good! Just finished work&#10;Person A: Nice! Want to grab dinner?&#10;Person B: Sure! Where?&#10;..."
              value={conversation}
              onChange={(e) => setConversation(e.target.value)}
              disabled={loading}
            />

            <div className="input-stats">
              <span className="char-count">
                {conversation.length} characters
              </span>
            </div>

            <button
              className="btn-generate"
              onClick={handleGenerateResponse}
              disabled={loading || processing || !conversation.trim()}
            >
              {loading ? '⏳ Uploading...' : processing ? '⏳ Processing...' : '✨ Generate Reply'}
            </button>

            {/* Tips Section */}
            <div className="tips-section">
              <h4>💭 How Personas Work</h4>
              <ul className="tips-list">
                <li><strong>Fresh Persona Each Time:</strong> Click "Next" or generate again → Get a completely new woman responding</li>
                <li><strong>Varies by Tone:</strong> Flirty conversation → Confident, playful woman. Serious → Thoughtful woman</li>
                <li><strong>Ask Questions:</strong> "What's your name?" → She'll introduce herself as a unique woman</li>
                <li><strong>Different Everytime:</strong> Same conversation, different persona each time you refresh/next</li>
              </ul>
            </div>
          </div>

          {/* Right Column - Output */}
          <div className="chat-section output-section">
            <h3>📤 AI Response</h3>

            {error && (
              <div className="error-message">
                <span>❌ {error}</span>
              </div>
            )}

            {/* Processing/Waiting State */}
            {processing && (
              <div className="processing-state">
                <span className="processing-spinner">⏳</span>
                <span className="processing-text">Waiting for AI reply...</span>
                {jobStatus && (
                  <span className="job-status">Status: {jobStatus}</span>
                )}
              </div>
            )}

            {response && !processing && (
              <div className="response-container">
                {/* Uniqueness Badge */}
                <div className={`uniqueness-badge ${isUnique ? 'unique' : 'rephrased'}`}>
                  {isUnique ? (
                    <>
                      <span className="badge-icon">✅</span>
                      <span className="badge-text">Completely Unique</span>
                    </>
                  ) : (
                    <>
                      <span className="badge-icon">🔄</span>
                      <span className="badge-text">Rephrased for Uniqueness</span>
                    </>
                  )}
                </div>

                {/* Response Text */}
                <div className="response-text">
                  <p>{response}</p>
                </div>

                {/* Action Buttons */}
                <div className="response-actions">
                  <button
                    className={`btn-copy ${copied ? 'copied' : ''}`}
                    onClick={handleCopyResponse}
                  >
                    {copied ? '✓ Copied!' : '📋 Copy'}
                  </button>
                  <button className="btn-next" onClick={handleNext}>
                    ➡️ Next
                  </button>
                </div>
              </div>
            )}

            {!response && !error && (
              <div className="empty-state">
                <p>Generate a response to see it here</p>
              </div>
            )}
          </div>
        </div>

        {/* Response History */}
        {responseHistory.length > 0 && (
          <div className="chat-history">
            <h3>📜 Session History</h3>
            <p className="history-description">
              Your responses from this session (not saved to database)
            </p>
            <div className="history-list">
              {responseHistory.map((item, index) => (
                <div key={index} className="history-item">
                  <div className="history-header">
                    <span className="history-number">#{index + 1}</span>
                    <span className="history-time">{item.timestamp}</span>
                    <span
                      className={`history-badge ${item.isUnique ? 'unique' : 'rephrased'}`}
                    >
                      {item.isUnique ? 'Unique' : 'Rephrased'}
                    </span>
                  </div>
                  <div className="history-content">
                    <p className="history-label">Response:</p>
                    <p className="history-text">{item.response}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Chat;
