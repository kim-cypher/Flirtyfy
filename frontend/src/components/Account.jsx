import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import { getCredits } from '../services/creditsAPI';
import './Account.css';

function Account() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);

  const [credits, setCredits] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getCredits().then((data) => { if (data.success) setCredits(data); }).catch(() => {});
  }, []);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const handleCopyLink = () => {
    if (!credits?.referral_link) return;
    navigator.clipboard.writeText(credits.referral_link).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="acct-root">
      <nav className="acct-nav">
        <span className="acct-logo">Flirtyfy</span>
        <div className="acct-nav-right">
          <button className="acct-nav-link" onClick={() => navigate('/dashboard')} type="button">Dashboard</button>
          <button className="acct-nav-link" onClick={() => navigate('/')} type="button">Chat</button>
          <button className="acct-logout" onClick={handleLogout} type="button">Logout</button>
        </div>
      </nav>

      <main className="acct-main">
        <button type="button" className="acct-back-btn" onClick={() => navigate(-1)} aria-label="Go back">
          ← Back
        </button>
        <h1 className="acct-title">Account</h1>

        <div className="acct-card">
          <h2 className="acct-card-title">Profile</h2>
          <div className="acct-profile-row">
            <span className="acct-profile-label">Username</span>
            <span className="acct-profile-value">{user?.username || '—'}</span>
          </div>
          <div className="acct-profile-row">
            <span className="acct-profile-label">Email</span>
            <span className="acct-profile-value">{user?.email || '—'}</span>
          </div>
          <div className="acct-profile-row">
            <span className="acct-profile-label">Plan</span>
            <span className={`acct-plan-badge${credits?.is_premium ? ' acct-plan-badge--premium' : ''}`}>
              {credits?.is_premium ? '⭐ Premium' : 'Free'}
            </span>
          </div>
          {credits && !credits.is_premium && (
            <button type="button" className="acct-subscribe-btn" onClick={() => navigate('/subscribe')}>
              Get more messages — from KSh {credits.plans?.topup?.price_kes ?? 170}
            </button>
          )}
        </div>

        {credits && (
          <div className="acct-card">
            <p className="acct-clicks">
              ⚡ <strong>{credits.is_premium ? 'Unlimited' : credits.available_clicks}</strong>
              {!credits.is_premium && ` click${credits.available_clicks === 1 ? '' : 's'} available`}
            </p>
            <h2 className="acct-card-title">Refer a friend, earn 30 free clicks</h2>
            <p className="acct-card-desc">
              Free for 7 days from the moment they join. Share your link below.
            </p>
            <div className="acct-referral-link-row">
              <input
                className="acct-referral-input"
                type="text"
                readOnly
                value={credits.referral_link}
                onFocus={(e) => e.target.select()}
              />
              <button type="button" className="acct-referral-copy" onClick={handleCopyLink}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default Account;
