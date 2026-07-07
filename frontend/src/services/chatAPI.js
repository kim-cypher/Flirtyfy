/**
 * Chat API Service
 * LEFT side:  generateSpecificResponse()
 * RIGHT side: generateButtonResponse(), getAvailableButtons()
 */

import apiClient from './apiClient';

// 40 button IDs — must match BUTTON_INTENTS keys in button_generator.py
const VALID_BUTTON_IDS = [
  // Row 1 — Opening & Re-entry
  'new_match', 'dead', 'you_went_silent', 'shower_fantasy', 'morning_flirt', 'after_work',
  // Row 2 — Emotional Connection
  'provider_energy', 'strategic_withdrawal', 'deep_emotion', 'lyrical_romance', 'vulnerability', 'family_talk',
  // Row 3 — Daily Life
  'lunch_break', 'dont_go', 'wine_stars', 'work_talk',
  // Row 4 — Fantasy & Romance
  'slow_dance', 'outdoor_fantasy', 'public_display', 'restaurant_fantasy', 'kitchen_flirt',
  // Row 5 — Personal & Deep
  'his_exes', 'secrets', 'long_without', 'bdsm_talk', 'kinky_at_work',
  // Row 6 — Sexual Escalation
  'sensual_echo', 'bedroom_questions', 'positions', 'bedtime_fantasies', 'toy_play', 'fetishes',
];

/**
 * Generate context-aware reply from pasted conversation (LEFT SIDE)
 * timeSlot: optional user-selected time override (e.g. 'evening').
 */
export const generateSpecificResponse = async (conversation, timeSlot = null) => {
  const trimmed = conversation.trim();
  if (!trimmed) throw new Error('Please paste a conversation');
  if (trimmed.length < 20) throw new Error(`Conversation too short (${trimmed.length} chars, need at least 20)`);
  if (trimmed.length > 10000) throw new Error(`Conversation too long (max 10000 characters)`);

  const payload = { conversation };
  if (timeSlot) payload.time_slot = timeSlot;

  try {
    const response = await apiClient.post('/chat/generate-specific/', payload);
    if (!response.data.success) throw new Error(response.data.message || 'Failed to generate response');
    return {
      success: true,
      response: response.data.response,
      replyId: response.data.reply_id || null,
      intent: response.data.intent,
      message: response.data.message,
    };
  } catch (error) {
    const err = new Error(error.response?.data?.message || error.message || 'Failed to generate response');
    err.outOfClicks = error.response?.status === 402 && error.response?.data?.out_of_clicks === true;
    throw err;
  }
};

/**
 * Generate button scenario message (RIGHT SIDE)
 * timeSlot: optional user-selected slot override (e.g. 'evening').
 * Sent to backend so temporal context reflects the user's chosen time, not server time.
 */
export const generateButtonResponse = async (buttonIntent, timeSlot = null) => {
  if (!buttonIntent) throw new Error('Button intent is required');
  if (!VALID_BUTTON_IDS.includes(buttonIntent)) throw new Error(`Unknown button: ${buttonIntent}`);

  const payload = { button_intent: buttonIntent };
  if (timeSlot) payload.time_slot = timeSlot;

  try {
    const response = await apiClient.post('/chat/generate-button/', payload);
    if (!response.data.success) throw new Error(response.data.message || 'Failed to generate response');
    return {
      success: true,
      response: response.data.response,
      replyId: response.data.reply_id || null,
      theme: response.data.theme,
      message: response.data.message,
    };
  } catch (error) {
    const err = new Error(error.response?.data?.message || error.message || `Failed to generate response for: ${buttonIntent}`);
    err.outOfClicks = error.response?.status === 402 && error.response?.data?.out_of_clicks === true;
    throw err;
  }
};

/**
 * All 40 buttons in order (left→right, top→bottom).
 * Row 7 buttons appear below a divider in RightPanel.

 * Rate a delivered reply — excellent | good | bad.
 * Fire-and-forget from the UI's perspective; failures are non-fatal.
 */
export const sendReplyFeedback = async (replyId, rating) => {
  const response = await apiClient.post('/chat/feedback/', { reply_id: replyId, rating });
  return response.data;
};

/**
 * All buttons in order (left→right, top→bottom).
 * emoji + shortLabel are used for the compact grid display.
 * description is used as tooltip title.
 */
export const getAvailableButtons = () => [
  // ── Row 1 — Opening & Re-entry ──────────────────────────────────────────
  { id: 'new_match',            emoji: '✨', shortLabel: 'New Match',    row: 1, description: 'First message after matching' },
  { id: 'dead',                 emoji: '💀', shortLabel: 'Dead Convo',   row: 1, description: 'He is cold — warm him back up without asking why' },
  { id: 'you_went_silent',      emoji: '⏰', shortLabel: 'Went Silent',  row: 1, description: 'He disappeared — re-enter warm, no confrontation' },
  { id: 'shower_fantasy',       emoji: '🚿', shortLabel: 'Shower',       row: 1, description: 'Alone or together — what the shower does to the mind' },
  { id: 'morning_flirt',        emoji: '🌅', shortLabel: 'Morning',      row: 1, description: 'Slow, warm, sensual morning energy' },
  { id: 'after_work',           emoji: '🛋️', shortLabel: 'After Work',   row: 1, description: 'Day is done — what do you reach for?' },

  // ── Row 2 — Emotional Connection ────────────────────────────────────────
  { id: 'provider_energy',      emoji: '🛡️', shortLabel: 'Quiet Strength', row: 2, description: 'Make him feel like a strong protector' },
  { id: 'strategic_withdrawal', emoji: '🍃', shortLabel: 'Need Space',   row: 2, description: 'Pull back so he chases harder' },
  { id: 'deep_emotion',         emoji: '💔', shortLabel: 'Deep Feel',    row: 2, description: 'Vulnerable admission — real and raw' },
  { id: 'lyrical_romance',      emoji: '💌', shortLabel: 'Sweet Words',  row: 2, description: 'Poetic, song-like intensity' },
  { id: 'vulnerability',        emoji: '💭', shortLabel: 'Vulnerable',   row: 2, description: 'The part you usually keep armored' },
  { id: 'family_talk',          emoji: '🏠', shortLabel: 'Family',       row: 2, description: 'How family shaped him — where he came from' },

  // ── Row 3 — Daily Life & Lifestyle ──────────────────────────────────────
  { id: 'lunch_break',          emoji: '🥗', shortLabel: 'Lunch',        row: 3, description: 'Midday — stolen time, who you think about' },
  { id: 'dont_go',              emoji: '🙏', shortLabel: 'Don\'t Go',    row: 3, description: 'He is leaving — a soft confession that makes him stay' },
  { id: 'wine_stars',           emoji: '🍷', shortLabel: 'Wine & Stars', row: 3, description: 'Wine, open sky, who you want beside you' },
  { id: 'work_talk',            emoji: '💼', shortLabel: 'Work Talk',    row: 3, description: 'What drives him — and what happens when work gets complicated' },

  // ── Row 4 — Fantasy & Romance ────────────────────────────────────────────
  { id: 'slow_dance',           emoji: '💃', shortLabel: 'Foreplay',     row: 4, description: 'How long, how slow, what he skips and should not' },
  { id: 'outdoor_fantasy',      emoji: '🌿', shortLabel: 'Outdoors',     row: 4, description: 'Outside, exposed, the risk of being seen — and wanting it' },
  { id: 'public_display',       emoji: '💋', shortLabel: 'Public PDA',   row: 4, description: 'Being claimed where people can see' },
  { id: 'restaurant_fantasy',   emoji: '🕯️', shortLabel: 'Restaurant',  row: 4, description: 'Restaurant vibes, best meals, and what happens under the table' },
  { id: 'kitchen_flirt',        emoji: '👩‍🍳', shortLabel: 'Kitchen',     row: 4, description: 'Apron only, held from behind, counter — the kitchen earns it' },

  // ── Row 5 — Personal & Deep ──────────────────────────────────────────────
  { id: 'his_exes',             emoji: '👻', shortLabel: 'His Exes',     row: 5, description: 'What was good, what he learned, who she was — curious, not jealous' },
  { id: 'secrets',              emoji: '🤫', shortLabel: 'Secrets',      row: 5, description: 'She shares one, then asks how he handles what he knows' },
  { id: 'long_without',         emoji: '⏳', shortLabel: 'No Touch',     row: 5, description: 'The quality of wanting in someone who waited' },
  { id: 'bdsm_talk',            emoji: '⛓️', shortLabel: 'BDSM',         row: 5, description: 'Power exchange, bondage, dominance, submission — which side he sits on' },
  { id: 'kinky_at_work',        emoji: '🖥️', shortLabel: 'Kinky Work',   row: 5, description: 'Closed doors, office proximity, explicit desire' },

  // ── Row 6 — Sexual Escalation ────────────────────────────────────────────
  { id: 'bedroom_questions',    emoji: '🛏️', shortLabel: 'Bedroom',      row: 6, description: 'Confess, then ask what he wants — explicitly' },
  { id: 'positions',            emoji: '😈', shortLabel: 'Positions',    row: 6, description: 'Go-to, what they reveal, what surprised her — and his' },
  { id: 'bedtime_fantasies',    emoji: '🌜', shortLabel: 'Bedtime',      row: 6, description: 'Unguarded hour — what you think about in the dark' },
  { id: 'toy_play',             emoji: '🎲', shortLabel: 'Toys',         row: 6, description: 'What you use, what you want him to use' },
  { id: 'fetishes',             emoji: '🎭', shortLabel: 'Fetishes',     row: 6, description: 'The specific edge where your desire gets interesting' },
];

const chatAPI = { generateSpecificResponse, generateButtonResponse, getAvailableButtons };
export default chatAPI;
