import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard';
import Chat from './components/Chat';
import FindLocation from './components/FindLocation';
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
 * - /locations - Find cities within 45 minutes of a state
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
          
          {/* Dashboard - user profile and settings */}
          <Route 
            path="/dashboard" 
            element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} 
          />
          
          {/* Find Location - search cities by state */}
          <Route 
            path="/locations" 
            element={isAuthenticated ? <FindLocation /> : <Navigate to="/login" />} 
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