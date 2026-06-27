/**
 * FlirtyfyLogo — the brand mark used in the header and auth pages.
 *
 * Design: a flame whose base has a chat-bubble tail.
 * Flame = desire/heat. Tail = conversation/messaging.
 * Gradient: rose-pink (bottom) → deep purple (top), matching the app palette.
 */

import React from 'react';

function FlirtyfyLogo({ size = 34, showText = true, textSize = 24 }) {
  const height = Math.round(size * 1.18);

  return (
    <div className="flirtyfy-logo" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {/* ── Icon ──────────────────────────────────────────────── */}
      <svg
        width={size}
        height={height}
        viewBox="0 0 32 38"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        style={{ flexShrink: 0 }}
      >
        <defs>
          <linearGradient id="flirtyGrad" x1="22" y1="38" x2="12" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0%"   stopColor="#d946a8" />
            <stop offset="55%"  stopColor="#9333ea" />
            <stop offset="100%" stopColor="#6c4fc9" />
          </linearGradient>
          <linearGradient id="flirtyGradInner" x1="16" y1="30" x2="16" y2="8" gradientUnits="userSpaceOnUse">
            <stop offset="0%"   stopColor="rgba(255,255,255,0.18)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0.04)" />
          </linearGradient>
        </defs>

        {/* Flame body — teardrop pointed at top */}
        <path
          d="M16 1C21 5 29 12 29 21C29 30 23 36 16 36C9 36 3 30 3 21C3 12 11 5 16 1Z"
          fill="url(#flirtyGrad)"
        />

        {/* Chat-bubble tail — bottom left, makes it a speech bubble */}
        <path
          d="M10 35L6.5 38.5L20 35.5Z"
          fill="url(#flirtyGrad)"
        />

        {/* Inner flame highlight — depth and warmth */}
        <path
          d="M16 9C16 9 22 15 22 21C22 25.5 19.5 28 16 28C12.5 28 10 25.5 10 21C10 15 16 9 16 9Z"
          fill="url(#flirtyGradInner)"
        />

        {/* Tiny specular highlight — top-left of flame */}
        <ellipse cx="12.5" cy="15" rx="2.2" ry="3.2" fill="rgba(255,255,255,0.18)" transform="rotate(-20 12.5 15)" />
      </svg>

      {/* ── Wordmark ──────────────────────────────────────────── */}
      {showText && (
        <span
          className="flirtyfy-wordmark"
          style={{ fontSize: textSize }}
          aria-label="Flirtyfy"
        >
          <span className="flirtyfy-word-flirty">Flirty</span>
          <span className="flirtyfy-word-fy">fy</span>
        </span>
      )}
    </div>
  );
}

export default FlirtyfyLogo;
