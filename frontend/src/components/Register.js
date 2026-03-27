import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../redux/actions/authActions';
import './Auth.css';

function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [ageMismatch, setAgeMismatch] = useState('');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector(state => state.auth);

  /**
   * Validate age when date of birth changes
   */
  const handleDateChange = (e) => {
    const selectedDate = new Date(e.target.value);
    const today = new Date();
    const age = today.getFullYear() - selectedDate.getFullYear();
    const monthDiff = today.getMonth() - selectedDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < selectedDate.getDate())) {
      // Subtract 1 from age if birthday hasn't occurred this year
      const actualAge = age - 1;
      if (actualAge < 18) {
        setAgeMismatch('You must be at least 18 years old to use Flirty');
      } else {
        setAgeMismatch('');
      }
    } else {
      if (age < 18) {
        setAgeMismatch('You must be at least 18 years old to use Flirty');
      } else {
        setAgeMismatch('');
      }
    }
    
    setDateOfBirth(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate all fields
    if (password !== confirmPassword) {
      alert('Passwords do not match');
      return;
    }
    
    if (!dateOfBirth) {
      alert('Please enter your date of birth');
      return;
    }
    
    if (ageMismatch) {
      alert(ageMismatch);
      return;
    }

    try {
      await dispatch(register(username, email, password, confirmPassword, dateOfBirth));
      navigate('/dashboard');
    } catch (err) {
      // Error is handled by Redux
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Register</h1>
        <p className="auth-notice">⚠️ Flirty is for adults 18+. Age verification is required.</p>
        {error && <div className="error-message">{error}</div>}
        {ageMismatch && <div className="error-message">{ageMismatch}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="dateOfBirth">Date of Birth <span className="required">*</span></label>
            <input
              type="date"
              id="dateOfBirth"
              value={dateOfBirth}
              onChange={handleDateChange}
              required
              disabled={loading}
            />
            <small className="form-hint">We verify you are 18+ to use this app</small>
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading || !!ageMismatch}>
            {loading ? 'Registering...' : 'Register'}
          </button>
        </form>
        <p className="auth-link">
          Already have an account? <Link to="/login">Login here</Link>
        </p>
      </div>
    </div>
  );
}

export default Register;