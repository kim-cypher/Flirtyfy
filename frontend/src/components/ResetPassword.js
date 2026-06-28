import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate, Link } from 'react-router-dom';
import { resetPassword } from '../redux/actions/authActions';
import FlirtyfyLogo from './FlirtyfyLogo';
import './Auth.css';

function ResetPassword() {
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (newPassword.length < 4) { setError('Password must be at least 4 characters.'); return; }
    if (newPassword !== confirmNewPassword) { setError('Passwords do not match.'); return; }
    setLoading(true);
    try {
      await dispatch(resetPassword(email, firstName, newPassword, confirmNewPassword));
      setSuccess(true);
      setTimeout(() => navigate('/login'), 1800);
    } catch (err) {
      setError(err.message || 'Password reset failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-root">
      <div className="auth-brand">
        <div className="auth-brand-inner">
          <div className="auth-brand-logomark">
            <FlirtyfyLogo size={44} textSize={30} />
          </div>
          <h2 className="auth-brand-headline">
            Forgot your<br />
            <span className="auth-brand-accent">password?</span>
          </h2>
          <p className="auth-brand-desc">
            No email link needed — just confirm your<br />email and first name to reset it.
          </p>
          <div className="auth-brand-dots">
            <span /><span /><span />
          </div>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-form-inner">
          <div className="auth-mobile-logo">
            <FlirtyfyLogo size={32} textSize={22} />
          </div>
          <h1 className="auth-form-title">Reset password</h1>
          <p className="auth-form-sub">Enter the email and first name you registered with.</p>

          {error && <div className="auth-error">{error}</div>}
          {success && <div className="auth-error" style={{ background: '#f0fbf0', borderColor: '#bce5bc', color: '#2a7a2a' }}>Password reset! Redirecting to login…</div>}

          {!success && (
            <form onSubmit={handleSubmit}>
              <div className="auth-field">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="you@example.com"
                />
              </div>
              <div className="auth-field">
                <label htmlFor="firstName">First name</label>
                <input
                  type="text"
                  id="firstName"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="Jane"
                />
              </div>
              <div className="auth-field">
                <label htmlFor="newPassword">New password</label>
                <input
                  type="password"
                  id="newPassword"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="At least 4 characters"
                />
              </div>
              <div className="auth-field">
                <label htmlFor="confirmNewPassword">Confirm new password</label>
                <input
                  type="password"
                  id="confirmNewPassword"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="At least 4 characters"
                />
              </div>
              <button type="submit" className="auth-submit" disabled={loading}>
                {loading ? 'Resetting…' : 'Reset password'}
              </button>
            </form>
          )}

          <p className="auth-switch">
            <Link to="/login">Back to sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default ResetPassword;
