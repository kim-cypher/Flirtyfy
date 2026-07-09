import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCredits, initiatePayment, getPaymentStatus } from '../services/creditsAPI';
import FlirtyfyLogo from './FlirtyfyLogo';
import './Subscribe.css';

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 120000; // give up after 2 minutes — user likely abandoned the phone prompt

function Subscribe() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState('');
  const [credits, setCredits] = useState(null);
  const [plan, setPlan] = useState('weekly'); // 'weekly' | 'topup' — weekly highlighted by default
  const [stage, setStage] = useState('form'); // form | pending | success | failed
  const [error, setError] = useState('');
  const pollRef = useRef(null);
  const pollStartRef = useRef(null);

  useEffect(() => {
    getCredits().then((data) => { if (data.success) setCredits(data); }).catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  const stopPolling = () => {
    clearInterval(pollRef.current);
    pollRef.current = null;
  };

  const pollStatus = (checkoutRequestId) => {
    pollStartRef.current = Date.now();
    pollRef.current = setInterval(async () => {
      if (Date.now() - pollStartRef.current > POLL_TIMEOUT_MS) {
        stopPolling();
        setStage('failed');
        setError('We did not hear back in time. If the payment went through, your clicks will still be added shortly — check back in a minute.');
        return;
      }
      try {
        const data = await getPaymentStatus(checkoutRequestId);
        if (data.status === 'success') {
          stopPolling();
          setStage('success');
        } else if (data.status === 'failed' || data.status === 'cancelled') {
          stopPolling();
          setStage('failed');
          setError('The payment was not completed. You can try again.');
        }
        // 'pending' — keep polling
      } catch (err) {
        // Transient network blip — keep polling, don't abort on one failed check.
      }
    }, POLL_INTERVAL_MS);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const trimmed = phone.trim();
    if (!trimmed) {
      setError('Please enter your M-Pesa phone number.');
      return;
    }
    setStage('pending');
    try {
      const data = await initiatePayment(trimmed, plan);
      if (!data.success) {
        setStage('failed');
        setError(data.message || 'Could not start the payment.');
        return;
      }
      pollStatus(data.checkout_request_id);
    } catch (err) {
      setStage('failed');
      setError(err.response?.data?.message || 'Could not start the payment. Please try again.');
    }
  };

  const handleRetry = () => {
    setStage('form');
    setError('');
  };

  const handleBackToChat = () => navigate('/');
  const handleBack = () => navigate(-1);

  return (
    <div className="sub-root">
      <button type="button" className="sub-back-btn" onClick={handleBack} aria-label="Go back">
        ← Back
      </button>
      <div className="sub-card">
        <FlirtyfyLogo size={32} textSize={22} />

        {credits && (
          <p className="sub-current-clicks">
            You currently have <strong>{credits.available_clicks}</strong> click{credits.available_clicks === 1 ? '' : 's'}.
          </p>
        )}

        {stage === 'form' && (
          <>
            <h2 className="sub-title">Choose your plan</h2>

            <div className="sub-plans">
              <button
                type="button"
                className={`sub-plan${plan === 'weekly' ? ' sub-plan--active' : ''}`}
                onClick={() => setPlan('weekly')}
              >
                <span className="sub-plan-badge">Best value</span>
                <span className="sub-plan-name">Weekly</span>
                <span className="sub-plan-price">
                  KSh {credits?.plans?.weekly?.price_kes ?? 1200}
                </span>
                <span className="sub-plan-desc">
                  A full week of heavy use — {credits?.plans?.weekly?.clicks ?? 1500} messages, valid 7 days
                </span>
              </button>

              <button
                type="button"
                className={`sub-plan${plan === 'topup' ? ' sub-plan--active' : ''}`}
                onClick={() => setPlan('topup')}
              >
                <span className="sub-plan-name">Top-up</span>
                <span className="sub-plan-price">
                  KSh {credits?.plans?.topup?.price_kes ?? 170}
                </span>
                <span className="sub-plan-desc">
                  {credits?.plans?.topup?.clicks ?? 200} messages — never expires
                </span>
              </button>
            </div>

            <p className="sub-sub">Paid securely via M-Pesa</p>

            <form onSubmit={handleSubmit} className="sub-form">
              <label className="sub-label" htmlFor="sub-phone">M-Pesa phone number</label>
              <input
                id="sub-phone"
                type="tel"
                className="sub-input"
                placeholder="07XX XXX XXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
              {error && <p className="sub-error">{error}</p>}
              <button type="submit" className="sub-pay-btn">
                Pay KSh {plan === 'weekly'
                  ? (credits?.plans?.weekly?.price_kes ?? 1200)
                  : (credits?.plans?.topup?.price_kes ?? 170)} with M-Pesa
              </button>
            </form>

            <p className="sub-hint">
              Prefer not to pay right now? Refer a friend instead — you both win.
              Share your link from your account page for 30 free bonus clicks.
            </p>
          </>
        )}

        {stage === 'pending' && (
          <div className="sub-status">
            <div className="sub-spinner" />
            <h2 className="sub-title">Check your phone</h2>
            <p className="sub-sub">Enter your M-Pesa PIN to complete the payment.</p>
          </div>
        )}

        {stage === 'success' && (
          <div className="sub-status">
            <div className="sub-check">✓</div>
            <h2 className="sub-title">Payment received!</h2>
            <p className="sub-sub">Your clicks have been added to your account.</p>
            <button type="button" className="sub-pay-btn" onClick={handleBackToChat}>
              Back to chat
            </button>
          </div>
        )}

        {stage === 'failed' && (
          <div className="sub-status">
            <h2 className="sub-title">Something went wrong</h2>
            <p className="sub-error">{error}</p>
            <button type="button" className="sub-pay-btn" onClick={handleRetry}>
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Subscribe;
