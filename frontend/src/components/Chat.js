/**
 * Chat Component - NEW Button System Interface
 * Split-screen design with context-aware and button responses
 * LEFT: Paste conversation for context-aware replies
 * RIGHT: 13 buttons for quick scenario responses
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import { getCredits } from '../services/creditsAPI';
import ChatInterface from './ChatInterface';
import FlirtyfyLogo from './FlirtyfyLogo';
import NotificationBell from './NotificationBell';
import './Chat.css';

const CREDITS_POLL_MS = 30000;

const TIME_SLOTS = [
  { id: 'late_night',    emoji: '🌙', label: '12–5am'  },
  { id: 'early_morning', emoji: '🌄', label: '5–9am'   },
  { id: 'morning',       emoji: '☀️', label: '9am–12'  },
  { id: 'midday',        emoji: '🌞', label: '12–2pm'  },
  { id: 'afternoon',     emoji: '🌤️', label: '2–6pm'   },
  { id: 'evening',       emoji: '🌆', label: '6–9pm'   },
  { id: 'night',         emoji: '🌃', label: '9pm–12'  },
];

function hourToSlot(h) {
  if (h >= 5  && h < 9)  return 'early_morning';
  if (h >= 9  && h < 12) return 'morning';
  if (h >= 12 && h < 14) return 'midday';
  if (h >= 14 && h < 18) return 'afternoon';
  if (h >= 18 && h < 21) return 'evening';
  if (h >= 21)            return 'night';
  return 'late_night';
}

function slotLabel(slotId) {
  return TIME_SLOTS.find(s => s.id === slotId)?.label || slotId;
}

// How long a manually-picked slot is trusted before we check in and ask
// whether the user still wants it, rather than silently reverting to real time.
const CHECK_IN_AFTER_MS = 3 * 60 * 60 * 1000; // 3 hours

function Chat() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);
  const token = localStorage.getItem('access_token');

  // Pre-select from browser local time. Auto-advances every minute like a clock
  // UNLESS the user manually picked a slot — manual picks are never silently overwritten.
  const [timeSlot, setTimeSlot] = useState(() => hourToSlot(new Date().getHours()));
  const [isManual, setIsManual] = useState(false);
  const [manualSetAt, setManualSetAt] = useState(null);
  const [checkInSlot, setCheckInSlot] = useState(null); // non-null while the modal is shown

  const [availableClicks, setAvailableClicks] = useState(null);

  const refreshCredits = useCallback(async () => {
    try {
      const data = await getCredits();
      if (data.success) setAvailableClicks(data.available_clicks);
    } catch (err) {
      // Silent — a failed poll shouldn't disrupt the UI.
    }
  }, []);

  useEffect(() => {
    refreshCredits();
    const id = setInterval(refreshCredits, CREDITS_POLL_MS);
    return () => clearInterval(id);
  }, [refreshCredits]);

  const handleChipClick = (slotId) => {
    setTimeSlot(slotId);
    setIsManual(true);
    setManualSetAt(Date.now());
    setCheckInSlot(null);
  };

  const tick = useCallback(() => {
    const autoSlot = hourToSlot(new Date().getHours());

    if (!isManual) {
      setTimeSlot(prev => prev !== autoSlot ? autoSlot : prev);
      return;
    }

    // Manual slot active — only check in once its trusted window has elapsed
    // AND real time has actually moved into a different slot.
    if (manualSetAt && Date.now() - manualSetAt >= CHECK_IN_AFTER_MS && autoSlot !== timeSlot) {
      setCheckInSlot(prev => prev ?? autoSlot);
    }
  }, [isManual, manualSetAt, timeSlot]);

  useEffect(() => {
    const id = setInterval(tick, 60000);
    return () => clearInterval(id);
  }, [tick]);

  const handleKeepManual = () => {
    setManualSetAt(Date.now()); // extend the trusted window
    setCheckInSlot(null);
  };

  const handleSwitchToAuto = () => {
    setIsManual(false);
    setManualSetAt(null);
    setTimeSlot(checkInSlot);
    setCheckInSlot(null);
  };

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const handleGoHome = () => {
    navigate('/dashboard');
  };

  return (
    <div className="chat-page">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <FlirtyfyLogo size={34} textSize={24} />
        </div>
        <div className="header-right">
          {availableClicks !== null && (
            <button
              className="credits-badge"
              onClick={() => navigate('/subscribe')}
              title="Click to top up"
              type="button"
            >
              ⚡ {availableClicks} click{availableClicks === 1 ? '' : 's'}
            </button>
          )}
          <NotificationBell />
          <button className="btn-nav" onClick={handleGoHome} title="Go to Dashboard">
            Home
          </button>
          {user && <span className="user-name">{user.username}</span>}
          <button className="btn-logout" onClick={handleLogout} title="Logout">
            Logout
          </button>
        </div>
      </div>

      {/* Global time bar — full width, applies to both panels */}
      <div className="time-bar" role="group" aria-label="Select time of day">
        <span className="time-bar-label">Time</span>
        {TIME_SLOTS.map((slot) => (
          <button
            key={slot.id}
            className={`time-chip${timeSlot === slot.id ? ' active' : ''}`}
            onClick={() => handleChipClick(slot.id)}
            type="button"
            aria-pressed={timeSlot === slot.id}
          >
            {slot.label}
          </button>
        ))}
      </div>

      {/* Main Chat Interface - Split Screen */}
      <div className="chat-interface-wrapper">
        <ChatInterface user={user} token={token} timeSlot={timeSlot} />
      </div>

      {/* Time check-in modal — only shown after a manual slot's trusted window elapses */}
      {checkInSlot && (
        <div className="time-checkin-overlay" role="dialog" aria-modal="true">
          <div className="time-checkin-modal">
            <p className="time-checkin-text">
              Still using <strong>{slotLabel(timeSlot)}</strong>, or switch to the current time
              (<strong>{slotLabel(checkInSlot)}</strong>)?
            </p>
            <div className="time-checkin-actions">
              <button type="button" className="time-checkin-btn keep" onClick={handleKeepManual}>
                Keep {slotLabel(timeSlot)}
              </button>
              <button type="button" className="time-checkin-btn switch" onClick={handleSwitchToAuto}>
                Switch to {slotLabel(checkInSlot)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Chat;