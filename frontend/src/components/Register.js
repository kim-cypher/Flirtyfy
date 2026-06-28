import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { register } from '../redux/actions/authActions';
import FlirtyfyLogo from './FlirtyfyLogo';
import './Auth.css';

// Eligible birth year range is listed first (most recently turned 18, going
// back), so users don't have to click a calendar back 18-100 years from
// today just to reach their own birth year.
const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 83 }, (_, i) => CURRENT_YEAR - 18 - i);
const MONTH_OPTIONS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function daysInMonth(month, year) {
  if (!month || !year) return 31;
  return new Date(year, month, 0).getDate();
}

function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [dobDay, setDobDay] = useState('');
  const [dobMonth, setDobMonth] = useState('');
  const [dobYear, setDobYear] = useState('');
  const [ageMismatch, setAgeMismatch] = useState('');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const referralCode = searchParams.get('ref') || '';
  const { loading, error } = useSelector(state => state.auth);

  const checkAge = (day, month, year) => {
    if (!day || !month || !year) { setAgeMismatch(''); return; }
    const selectedDate = new Date(year, month - 1, day);
    const today = new Date();
    let age = today.getFullYear() - selectedDate.getFullYear();
    const monthDiff = today.getMonth() - selectedDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < selectedDate.getDate())) {
      age -= 1;
    }
    setAgeMismatch(age < 18 ? 'You must be at least 18 years old to use Flirtyfy' : '');
  };

  const handleDayChange = (e) => { setDobDay(e.target.value); checkAge(e.target.value, dobMonth, dobYear); };
  const handleMonthChange = (e) => { setDobMonth(e.target.value); checkAge(dobDay, e.target.value, dobYear); };
  const handleYearChange = (e) => { setDobYear(e.target.value); checkAge(dobDay, dobMonth, e.target.value); };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!EMAIL_RE.test(email.trim())) { alert('Please enter a valid email address (e.g. you@example.com)'); return; }
    if (password.length < 4) { alert('Password must be at least 4 characters.'); return; }
    if (password !== confirmPassword) { alert('Passwords do not match'); return; }
    if (!dobDay || !dobMonth || !dobYear) { alert('Please enter your date of birth'); return; }
    if (ageMismatch) { alert(ageMismatch); return; }
    const dateOfBirth = `${dobYear}-${String(dobMonth).padStart(2, '0')}-${String(dobDay).padStart(2, '0')}`;
    try {
      await dispatch(register(username, email, firstName, password, confirmPassword, dateOfBirth, referralCode));
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
              <label>Date of Birth</label>
              <div className="auth-dob-row">
                <select value={dobDay} onChange={handleDayChange} required disabled={loading}>
                  <option value="">Day</option>
                  {Array.from({ length: daysInMonth(dobMonth, dobYear) }, (_, i) => i + 1).map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
                <select value={dobMonth} onChange={handleMonthChange} required disabled={loading}>
                  <option value="">Month</option>
                  {MONTH_OPTIONS.map((m, i) => (
                    <option key={m} value={i + 1}>{m}</option>
                  ))}
                </select>
                <select value={dobYear} onChange={handleYearChange} required disabled={loading}>
                  <option value="">Year</option>
                  {YEAR_OPTIONS.map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>
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
                placeholder="At least 4 characters"
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
