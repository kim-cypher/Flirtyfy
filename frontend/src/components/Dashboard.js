import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import './Dashboard.css';

/**
 * Dashboard Component
 * 
 * User profile and settings page
 * Features:
 * - Display user information (username, email)
 * - Navigation to Chat and FindLocation features
 * - Logout functionality
 */
function Dashboard() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);

  /**
   * Handle logout
   */
  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  /**
   * Navigate to Chat page
   */
  const handleGoToChat = () => {
    navigate('/');
  };

  /**
   * Navigate to Find Location page
   */
  const handleGoToLocations = () => {
    navigate('/locations');
  };

  return (
    <div className="dashboard-container">
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="nav-left">
          <h2>💬 Flirty</h2>
        </div>
        <div className="nav-center">
          <button className="nav-btn" onClick={handleGoToChat}>
            💬 Chat
          </button>
          <button className="nav-btn" onClick={handleGoToLocations}>
            📍 Find Location
          </button>
          <button className="nav-btn active">Profile</button>
        </div>
        <div className="nav-right">
          <span className="user-info-nav">Welcome, {user?.username}!</span>
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Features Navigation */}
        <div className="features-section">
          <h3>🚀 Available Features</h3>
          <div className="features-grid">
            {/* Chat Feature */}
            <div className="feature-card">
              <div className="feature-icon">💬</div>
              <h4>AI Chat</h4>
              <p>Get natural, human-like replies to your conversations. Our AI generates unique responses that never repeat.</p>
              <button 
                className="btn-feature"
                onClick={handleGoToChat}
              >
                Go to Chat
              </button>
            </div>

            {/* Find Location Feature */}
            <div className="feature-card">
              <div className="feature-icon">📍</div>
              <h4>Find Location</h4>
              <p>Discover cities exactly 45 minutes away from any US state. Explore nearby destinations with population and coordinates.</p>
              <button 
                className="btn-feature"
                onClick={handleGoToLocations}
              >
                Find Cities
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;