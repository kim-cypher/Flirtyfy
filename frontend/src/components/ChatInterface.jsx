import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useNavigate } from 'react-router-dom';
import LeftPanel from './LeftPanel';
import RightPanel from './RightPanel';
import OutputArea from './OutputArea';
import { generateSpecificResponse, generateButtonResponse } from '../services/chatAPI';
import './ChatInterface.css';

function ChatInterface({ user, token, timeSlot, onOpenTimeModal }) {
  const navigate = useNavigate();
  const [leftResponse, setLeftResponse] = useState('');
  const [leftReplyId, setLeftReplyId] = useState(null);
  const [leftLoading, setLeftLoading] = useState(false);
  const [leftError, setLeftError] = useState('');

  const [rightResponse, setRightResponse] = useState('');
  const [rightReplyId, setRightReplyId] = useState(null);
  const [rightLoading, setRightLoading] = useState(false);
  const [rightLoadingButton, setRightLoadingButton] = useState(null);
  const [rightError, setRightError] = useState('');

  const handleLeftGenerate = async (conversation) => {
    setLeftLoading(true);
    setLeftError('');
    setLeftResponse('');
    setLeftReplyId(null);

    try {
      const result = await generateSpecificResponse(conversation, timeSlot);
      setLeftResponse(result.response);
      setLeftReplyId(result.replyId);
    } catch (error) {
      if (error.outOfClicks) {
        navigate('/subscribe');
        return;
      }
      setLeftError(error.message || 'Failed to generate response');
    } finally {
      setLeftLoading(false);
    }
  };

  const handleRightButtonClick = async (buttonIntent) => {
    setRightLoading(true);
    setRightLoadingButton(buttonIntent);
    setRightError('');
    setRightResponse('');
    setRightReplyId(null);

    try {
      const result = await generateButtonResponse(buttonIntent, timeSlot);
      setRightResponse(result.response);
      setRightReplyId(result.replyId);
    } catch (error) {
      if (error.outOfClicks) {
        navigate('/subscribe');
        return;
      }
      setRightError(error.message || 'Failed to generate response');
    } finally {
      setRightLoading(false);
      setRightLoadingButton(null);
    }
  };

  return (
    <div className="chat-interface">
      <div className="interface-side interface-left">
        <div className="side-content">
          <LeftPanel
            onGenerate={handleLeftGenerate}
            loading={leftLoading}
          />
          
          <div className="output-wrapper">
            <OutputArea
              response={leftResponse}
              replyId={leftReplyId}
              loading={leftLoading}
              error={leftError}
            />
          </div>
        </div>
      </div>

      <div className="interface-divider" />

      <div className="interface-side interface-right">
        <div className="side-content">
          <RightPanel
            onButtonClick={handleRightButtonClick}
            loading={rightLoading}
            loadingButton={rightLoadingButton}
            onOpenTimeModal={onOpenTimeModal}
          />
          
          <div className="output-wrapper">
            <OutputArea
              response={rightResponse}
              replyId={rightReplyId}
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
  timeSlot: PropTypes.string,
  onOpenTimeModal: PropTypes.func,
};

ChatInterface.defaultProps = {
  user: null,
  token: null,
  timeSlot: null,
  onOpenTimeModal: () => {},
};

export default ChatInterface;
