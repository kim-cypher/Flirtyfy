/**
 * Chat Component - NEW Button System Interface
 * Split-screen design with context-aware and button responses
 * LEFT: Paste conversation for context-aware replies
 * RIGHT: 13 buttons for quick scenario responses
 */

import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import ChatInterface from './ChatInterface';
import './Chat.css';

function Chat() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);
  const token = localStorage.getItem('access_token');

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const handleGoHome = () => {
    navigate('/dashboard');
  };

  return (
    <div className="chat-page">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <h1>🔥 Button System - Responses</h1>
          <p className="header-subtitle">LEFT: Paste conversations | RIGHT: Quick scenarios</p>
        </div>
        <div className="header-right">
          <button className="btn-nav" onClick={handleGoHome} title="Go to Dashboard">
            Home
          </button>
          {user && <span className="user-name">{user.username}</span>}
          <button className="btn-logout" onClick={handleLogout} title="Logout">
            Logout
          </button>
        </div>
      </div>

      {/* Main Chat Interface - Split Screen */}
      <div className="chat-interface-wrapper">
        <ChatInterface user={user} token={token} />
      </div>
    </div>
  );
}

export default Chat;