import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { register } from '../redux/actions/authActions';
import FlirtyfyLogo from './FlirtyfyLogo';
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
  const [searchParams] = useSearchParams();
  const referralCode = searchParams.get('ref') || '';
  const { loading, error } = useSelector(state => state.auth);

  const handleDateChange = (e) => {
    const selectedDate = new Date(e.target.value);
    const today = new Date();
    const age = today.getFullYear() - selectedDate.getFullYear();
    const monthDiff = today.getMonth() - selectedDate.getMonth();
    const actualAge =
      monthDiff < 0 || (monthDiff === 0 && today.getDate() < selectedDate.getDate())
        ? age - 1
        : age;
    setAgeMismatch(actualAge < 18 ? 'You must be at least 18 years old to use Flirtyfy' : '');
    setDateOfBirth(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) { alert('Passwords do not match'); return; }
    if (!dateOfBirth) { alert('Please enter your date of birth'); return; }
    if (ageMismatch) { alert(ageMismatch); return; }
    try {
      await dispatch(register(username, email, password, confirmPassword, dateOfBirth, referralCode));
      navigate('/dashboard');
    } catch (err) {}
  };

  return (
    <div className="auth-root">
      <div className="auth-brand">
        <div className="auth-brand-inner">
          <div className="auth-brand-logomark">
            <FlirtyfyLogo size={44} textSize={30} />
          </div>
          <h2 className="auth-brand-headline">
            Join the<br />
            <span className="auth-brand-accent">conversation.</span>
          </h2>
          <p className="auth-brand-desc">
            AI-powered replies that feel real.<br />Never robotic. Never repeating.
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
          <h1 className="auth-form-title">Create account</h1>
          <p className="auth-form-sub">Adults 18+ only</p>
          {referralCode && (
            <p className="auth-form-sub" style={{ color: '#9b78f0' }}>
              You were invited by a friend — you'll both benefit once you sign up.
            </p>
          )}

          {error && <div className="auth-error">{error}</div>}
          {ageMismatch && <div className="auth-error">{ageMismatch}</div>}

          <form onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={loading}
                placeholder="yourname"
              />
            </div>
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
              <label htmlFor="dateOfBirth">Date of Birth</label>
              <input
                type="date"
                id="dateOfBirth"
                value={dateOfBirth}
                onChange={handleDateChange}
                required
                disabled={loading}
              />
            </div>
            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="••••••••"
              />
            </div>
            <div className="auth-field">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              className="auth-submit"
              disabled={loading || !!ageMismatch}
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Register;
