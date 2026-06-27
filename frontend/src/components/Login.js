import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link } from 'react-router-dom';
import { login } from '../redux/actions/authActions';
import FlirtyfyLogo from './FlirtyfyLogo';
import './Auth.css';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector(state => state.auth);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await dispatch(login(email, password));
      navigate('/dashboard');
    } catch (err) {}
  };

  return (
    <div className="auth-root">
      <div className="auth-brand">
        <div className="auth-brand-inner">
          <div className="auth-brand-logomark">F</div>
          <h2 className="auth-brand-headline">
            Words that<br />
            <span className="auth-brand-accent">do the work.</span>
          </h2>
          <p className="auth-brand-desc">
            Smart replies. Perfect timing.<br />Every message lands exactly right.
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
          <h1 className="auth-form-title">Welcome back</h1>
          <p className="auth-form-sub">Sign in to your account</p>

          {error && <div className="auth-error">{error}</div>}

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
            <button type="submit" className="auth-submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="auth-switch">
            No account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
