import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import { getCredits } from '../services/creditsAPI';
import './Dashboard.css';

const MESSAGES = [
  "Still here, thinking about exactly what you said and what it says about you. What would you do with me right now if absolutely nothing was stopping you?",
  "I have been restless since this morning and I am done pretending otherwise. What is the most honest thing you have ever told a woman when you realized she actually meant it?",
  "Not managed, not even a little bit since you said that. When was the last time you wanted someone this clearly and actually did something about it?",
  "Lights low, settled into this, not going anywhere. What would you ask me to do first if I told you I wanted to follow your lead right now?",
  "Already leaning into this more than I planned to tonight. What is it about a woman being this direct that pulls you in completely?",
  "Honest thing, I keep catching myself thinking about this when I should be doing other things. Would you do anything about it if you knew exactly what I was thinking?",
  "Can't stop, and I am not sure I want to. What does it do to you when a woman says out loud what most women only think?",
];

function Dashboard() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);

  const [msgIndex, setMsgIndex] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [charIndex, setCharIndex] = useState(0);
  const [phase, setPhase] = useState('typing');
  const [visible, setVisible] = useState(true);

  const [credits, setCredits] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getCredits().then((data) => { if (data.success) setCredits(data); }).catch(() => {});
  }, []);

  const handleCopyLink = () => {
    if (!credits?.referral_link) return;
    navigator.clipboard.writeText(credits.referral_link).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  useEffect(() => {
    const msg = MESSAGES[msgIndex];

    if (phase === 'typing') {
      if (charIndex < msg.length) {
        const t = setTimeout(() => {
          setDisplayText(msg.slice(0, charIndex + 1));
          setCharIndex(c => c + 1);
        }, 38);
        return () => clearTimeout(t);
      } else {
        const t = setTimeout(() => setPhase('fading'), 2800);
        return () => clearTimeout(t);
      }
    }

    if (phase === 'fading') {
      setVisible(false);
      const t = setTimeout(() => {
        setDisplayText('');
        setCharIndex(0);
        setMsgIndex(i => (i + 1) % MESSAGES.length);
        setVisible(true);
        setPhase('typing');
      }, 520);
      return () => clearTimeout(t);
    }
  }, [phase, charIndex, msgIndex]);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const handleGetStarted = () => navigate('/');

  return (
    <div className="db-root">
      <nav className="db-nav">
        <span className="db-logo">Flirtyfy</span>
        <div className="db-nav-right">
          {user?.username && <span className="db-welcome">{user.username}</span>}
          <button className="db-logout" onClick={handleLogout}>Logout</button>
        </div>
      </nav>

      <main className="db-stage">
        <p className="db-label">AI · Live Preview</p>

        <div className={`db-bubble ${visible ? 'db-bubble--visible' : 'db-bubble--hidden'}`}>
          <span className="db-text">{displayText}</span>
          <span className={`db-cursor ${phase === 'typing' ? 'db-cursor--on' : ''}`}>|</span>
        </div>

        <button className="db-cta" onClick={handleGetStarted}>
          Make it yours <span className="db-arrow">→</span>
        </button>

        {credits && (
          <div className="db-referral-card">
            <p className="db-referral-clicks">
              ⚡ <strong>{credits.available_clicks}</strong> click{credits.available_clicks === 1 ? '' : 's'} available
            </p>
            <p className="db-referral-title">Refer a friend, earn 30 free clicks</p>
            <p className="db-referral-desc">
              Free for 7 days from the moment they join. Share your link below.
            </p>
            <div className="db-referral-link-row">
              <input
                className="db-referral-input"
                type="text"
                readOnly
                value={credits.referral_link}
                onFocus={(e) => e.target.select()}
              />
              <button type="button" className="db-referral-copy" onClick={handleCopyLink}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <button type="button" className="db-referral-topup" onClick={() => navigate('/subscribe')}>
              Or top up — ${credits.subscription_price_usd} for {credits.subscription_clicks} clicks
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default Dashboard;
