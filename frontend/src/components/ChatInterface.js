/**
 * ChatInterface Component - Split-Screen Chat with Button System
 * LEFT PANE: Context area for pasting conversations
 * RIGHT PANE: 13 Quick-response buttons with text area
 */

import React, { useState, useRef, useEffect } from 'react';
import { uploadChat, fetchLatestReply } from '../services/chatService';
import './ChatInterface.css';

function ChatInterface({ user, token }) {
  // Left pane state
  const [conversation, setConversation] = useState('');

  // Right pane state
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [responseText, setResponseText] = useState('');
  const [generatedReply, setGeneratedReply] = useState('');
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');

  const pollIntervalRef = useRef(null);
  const timeoutRef = useRef(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  // Button scenarios
  const scenarios = [
    { id: 1, label: 'Romantic', emoji: '💕' },
    { id: 2, label: 'Funny', emoji: '😂' },
    { id: 3, label: 'Mysterious', emoji: '🤫' },
    { id: 4, label: 'Flirty', emoji: '😉' },
    { id: 5, label: 'Confident', emoji: '💪' },
    { id: 6, label: 'Playful', emoji: '🎮' },
    { id: 7, label: 'Sarcastic', emoji: '🙄' },
    { id: 8, label: 'Sincere', emoji: '❤️' },
    { id: 9, label: 'Witty', emoji: '🧠' },
    { id: 10, label: 'Subtle', emoji: '👀' },
    { id: 11, label: 'Bold', emoji: '🔥' },
    { id: 12, label: 'Sweet', emoji: '🍫' },
    { id: 13, label: 'Teasing', emoji: '😏' },
  ];

  const handleScenarioSelect = (scenario) => {
    setSelectedScenario(scenario);
    setError('');
    setGeneratedReply('');
    setResponseText('');
  };

  const handleResponseTextChange = (e) => {
    setResponseText(e.target.value);
  };

  const handleGenerateResponse = async () => {
    if (!conversation.trim()) {
      setError('Please paste a conversation on the left pane');
      return;
    }

    if (!selectedScenario) {
      setError('Please select a scenario');
      return;
    }

    if (!responseText.trim()) {
      setError('Please add your response text');
      return;
    }

    const fullContext = `Scenario: ${selectedScenario.label} (${selectedScenario.emoji})\n\nYour response to add context to:\n${responseText}\n\nFull conversation context:\n${conversation}`;

    setLoading(true);
    setError('');
    setGeneratedReply('');
    setProcessing(false);

    try {
      const result = await uploadChat(fullContext);

      if (result && result.id) {
        setProcessing(true);
        setLoading(false);

        const pollFunction = async () => {
          try {
            const latestReply = await fetchLatestReply();

            if (latestReply && latestReply.length > 0) {
              const latest = latestReply[0];
              if ((latest.status === 'complete' || latest.status === 'completed') && latest.original_text) {
                setGeneratedReply(latest.original_text);
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
      setError(err.message || 'Failed to generate response');
      setLoading(false);
    }
  };

  const handleCopyResponse = () => {
    if (generatedReply) {
      navigator.clipboard.writeText(generatedReply);
    }
  };

  const handleReset = () => {
    setSelectedScenario(null);
    setResponseText('');
    setGeneratedReply('');
    setError('');
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
    <div className="chat-interface">
      {/* LEFT PANE: Conversation Context */}
      <div className="chat-pane left-pane">
        <div className="pane-header">
          <h2>📝 Conversation Context</h2>
          <p className="pane-subtext">Paste the conversation for context-aware responses</p>
        </div>
        <textarea
          className="context-textarea"
          placeholder="Paste the full conversation here to give context to your response..."
          value={conversation}
          onChange={(e) => setConversation(e.target.value)}
          disabled={loading || processing}
        />
      </div>

      {/* DIVIDER */}
      <div className="chat-divider"></div>

      {/* RIGHT PANE: Scenario Buttons + Response Area */}
      <div className="chat-pane right-pane">
        <div className="pane-header">
          <h2>🎯 Response Generator</h2>
          <p className="pane-subtext">Select tone, add your text, then generate</p>
        </div>

        {/* Scenario Buttons Grid */}
        <div className="scenarios-grid">
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              className={`scenario-btn ${selectedScenario?.id === scenario.id ? 'active' : ''}`}
              onClick={() => handleScenarioSelect(scenario)}
              disabled={loading || processing}
              title={scenario.label}
            >
              <span className="scenario-emoji">{scenario.emoji}</span>
              <span className="scenario-label">{scenario.label}</span>
            </button>
          ))}
        </div>

        {/* Response Text Area */}
        <div className="response-input-section">
          <label className="input-label">Your Response:</label>
          <textarea
            className="response-textarea"
            placeholder="Enter your response text that will be given context and enhanced..."
            value={responseText}
            onChange={handleResponseTextChange}
            disabled={loading || processing}
          />
        </div>

        {/* Action Buttons */}
        <div className="action-buttons">
          <button
            className={`btn-generate-response ${loading || processing ? 'loading' : ''}`}
            onClick={handleGenerateResponse}
            disabled={loading || processing || !conversation.trim() || !responseText.trim() || !selectedScenario}
          >
            {loading ? 'Uploading...' : processing ? 'Generating...' : 'Generate Response'}
          </button>
          <button
            className="btn-reset"
            onClick={handleReset}
            disabled={loading || processing}
          >
            Reset
          </button>
        </div>

        {/* Error Message */}
        {error && <div className="error-message">{error}</div>}

        {/* Generated Reply Output */}
        <div className="reply-output">
          <label className="output-label">Generated Reply:</label>
          <div className="output-container">
            {processing && !generatedReply && (
              <div className="processing-indicator">
                <div className="spinner"></div>
                <p>Generating your context-aware response...</p>
              </div>
            )}
            {generatedReply && (
              <div className="reply-content">
                <div className="reply-text">{generatedReply}</div>
                <div className="reply-footer">
                  <button className="btn-copy-reply" onClick={handleCopyResponse}>
                    📋 Copy
                  </button>
                </div>
              </div>
            )}
            {!generatedReply && !processing && (
              <div className="placeholder-output">
                Your enhanced response will appear here
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
