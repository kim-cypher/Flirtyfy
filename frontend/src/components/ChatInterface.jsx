/**
 * ChatInterface Component
 * Main container with split-screen layout (50/50)
 * LEFT: Textarea input + Response output
 * RIGHT: 13 Buttons + Response output
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import LeftPanel from './LeftPanel';
import RightPanel from './RightPanel';
import OutputArea from './OutputArea';
import { generateSpecificResponse, generateButtonResponse } from '../services/chatAPI';
import './ChatInterface.css';

function ChatInterface({ user, token }) {
  // LEFT SIDE state
  const [leftResponse, setLeftResponse] = useState('');
  const [leftIntent, setLeftIntent] = useState(null);
  const [leftLoading, setLeftLoading] = useState(false);
  const [leftError, setLeftError] = useState('');

  // RIGHT SIDE state
  const [rightResponse, setRightResponse] = useState('');
  const [rightTheme, setRightTheme] = useState('');
  const [rightLoading, setRightLoading] = useState(false);
  const [rightLoadingButton, setRightLoadingButton] = useState(null);
  const [rightError, setRightError] = useState('');

  /**
   * Handle LEFT SIDE generate
   */
  const handleLeftGenerate = async (conversation) => {
    setLeftLoading(true);
    setLeftError('');
    setLeftResponse('');
    setLeftIntent(null);

    try {
      const result = await generateSpecificResponse(conversation);
      setLeftResponse(result.response);
      setLeftIntent(result.intent);
    } catch (error) {
      setLeftError(error.message || 'Failed to generate response');
    } finally {
      setLeftLoading(false);
    }
  };

  /**
   * Handle RIGHT SIDE button click
   */
  const handleRightButtonClick = async (buttonIntent) => {
    setRightLoading(true);
    setRightLoadingButton(buttonIntent);
    setRightError('');
    setRightResponse('');
    setRightTheme('');

    try {
      const result = await generateButtonResponse(buttonIntent);
      setRightResponse(result.response);
      setRightTheme(result.theme);
    } catch (error) {
      setRightError(error.message || 'Failed to generate response');
    } finally {
      setRightLoading(false);
      setRightLoadingButton(null);
    }
  };

  /**
   * Retry LEFT SIDE
   */
  const handleLeftRetry = (conversation) => {
    if (conversation.trim()) {
      handleLeftGenerate(conversation);
    }
  };

  /**
   * Retry RIGHT SIDE
   */
  const handleRightRetry = (buttonIntent) => {
    if (buttonIntent) {
      handleRightButtonClick(buttonIntent);
    }
  };

  return (
    <div className="chat-interface">
      {/* LEFT SIDE */}
      <div className="interface-side interface-left">
        <div className="side-content">
          <LeftPanel
            onGenerate={handleLeftGenerate}
            loading={leftLoading}
          />
          
          <div className="output-wrapper">
            <OutputArea
              response={leftResponse}
              intent={leftIntent}
              loading={leftLoading}
              error={leftError}
            />
          </div>
        </div>
      </div>

      {/* DIVIDER */}
      <div className="interface-divider"></div>

      {/* RIGHT SIDE */}
      <div className="interface-side interface-right">
        <div className="side-content">
          <RightPanel
            onButtonClick={handleRightButtonClick}
            loading={rightLoading}
            loadingButton={rightLoadingButton}
          />
          
          <div className="output-wrapper">
            <OutputArea
              response={rightResponse}
              theme={rightTheme}
              loading={rightLoading}
              error={rightError}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

ChatInterface.propTypes = {
  user: PropTypes.shape({
    id: PropTypes.number,
    username: PropTypes.string,
    email: PropTypes.string,
  }),
  token: PropTypes.string,
};

ChatInterface.defaultProps = {
  user: null,
  token: null,
};

export default ChatInterface;
