import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard';
import Chat from './components/Chat';
import Subscribe from './components/Subscribe';
import Account from './components/Account';
import './App.css';

/**
 * App Component
 * 
 * Main application component that handles:
 * - Routing between authenticated and unauthenticated pages
 * - Authentication-based navigation
 * - Page layout
 * 
 * Routes:
 * - /login - Login page (only for unauthenticated users)
 * - /register - Registration page (only for unauthenticated users)
 * - / - Chat page (default landing page for authenticated users)
 * - /dashboard - Profile/settings dashboard
 */
function App() {
  const isAuthenticated = useSelector(state => state.auth.isAuthenticated);

  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Auth Routes - only accessible if NOT authenticated */}
          <Route 
            path="/login" 
            element={!isAuthenticated ? <Login /> : <Navigate to="/" />} 
          />
          <Route 
            path="/register" 
            element={!isAuthenticated ? <Register /> : <Navigate to="/" />} 
          />

          {/* Main Routes - only accessible if authenticated */}
          {/* Chat is the default landing page */}
          <Route 
            path="/" 
            element={isAuthenticated ? <Chat /> : <Navigate to="/login" />} 
          />
          
          {/* Dashboard - AI preview + CTA */}
          <Route
            path="/dashboard"
            element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />}
          />

          {/* Account - profile, plan, subscribe, referral */}
          <Route
            path="/account"
            element={isAuthenticated ? <Account /> : <Navigate to="/login" />}
          />

          {/* Subscribe - top up clicks via M-Pesa */}
          <Route
            path="/subscribe"
            element={isAuthenticated ? <Subscribe /> : <Navigate to="/login" />}
          />


          {/* Fallback - redirect to appropriate page */}
          <Route 
            path="*" 
            element={<Navigate to={isAuthenticated ? "/" : "/login"} />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;