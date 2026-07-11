/**
 * Chat API Service
 * LEFT side:  generateSpecificResponse()
 * RIGHT side: generateButtonResponse(), getAvailableButtons()
 */

import apiClient from './apiClient';

// Button IDs — must match BUTTON_INTENTS keys in button_generator.py.
// Only two user-facing buttons now; the left panel handles conversations.
const VALID_BUTTON_IDS = ['new_match', 'vulnerability', 'reply_trigger'];

/**
 * Generate context-aware reply from pasted conversation (LEFT SIDE)
 * timeSlot: optional user-selected time override (e.g. 'evening').
 */
export const generateSpecificResponse = async (conversation, timeSlot = null, hisLastN = 1) => {
  const trimmed = conversation.trim();
  if (!trimmed) throw new Error('Please paste a conversation');
  if (trimmed.length < 20) throw new Error(`Conversation too short (${trimmed.length} chars, need at least 20)`);
  if (trimmed.length > 10000) throw new Error(`Conversation too long (max 10000 characters)`);

  const payload = { conversation };
  if (timeSlot) payload.time_slot = timeSlot;
  if (hisLastN && hisLastN > 1) payload.his_last_n = hisLastN;

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
    // Server refused to ship a near-duplicate (ban-safety). Signal a silent
    // auto-retry rather than surfacing a message to the user.
    if (response.data.retry) return { retry: true };
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
 * Rate a delivered reply — excellent | good | bad.
 * Fire-and-forget from the UI's perspective; failures are non-fatal.
 */
export const sendReplyFeedback = async (replyId, rating) => {
  const response = await apiClient.post('/chat/feedback/', { reply_id: replyId, rating });
  return response.data;
};

/**
 * The two user-facing buttons. New Match opens a fresh chat; Vulnerable is a
 * raw confession. Everything conversation-driven lives in the left panel.
 */
export const getAvailableButtons = () => [
  { id: 'new_match',     emoji: '✨', shortLabel: 'New Match',       row: 1, description: 'Break the ice — a warm, easy first message' },
  { id: 'vulnerability', emoji: '💭', shortLabel: 'Vulnerable',      row: 1, description: 'A raw, honest confession that pulls him closer' },
  { id: 'reply_trigger', emoji: '💔', shortLabel: 'Reply to Trigger', row: 1, description: 'He went quiet — nudge him back with playful feeling' },
];

const chatAPI = { generateSpecificResponse, generateButtonResponse, getAvailableButtons };
export default chatAPI;
