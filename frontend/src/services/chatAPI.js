/**
 * Chat API Service - Button System Integration
 * Handles calls to the two new endpoints:
 * - POST /api/chat/generate-specific/ (LEFT side - context-aware)
 * - POST /api/chat/generate-button/ (RIGHT side - button scenarios)
 */

import apiClient from './apiClient';

/**
 * Generate context-aware response from pasted conversation (LEFT SIDE)
 * @param {string} conversation - Pasted conversation text (min 20, max 10000 chars)
 * @returns {Promise} Response with: success, response, intent (topic, tone, stage, energy)
 */
export const generateSpecificResponse = async (conversation) => {
  // Validate input
  const trimmed = conversation.trim();
  
  if (!trimmed) {
    throw new Error('Please paste a conversation');
  }
  
  if (trimmed.length < 20) {
    throw new Error(`Conversation too short (${trimmed.length} chars, need at least 20)`);
  }
  
  if (trimmed.length > 10000) {
    throw new Error(`Conversation too long (${trimmed.length} chars, max 10000)`);
  }
  
  try {
    const response = await apiClient.post('/chat/generate-specific/', {
      conversation: conversation,
    });
    
    // Verify response structure
    if (!response.data.success) {
      throw new Error(response.data.message || 'Failed to generate response');
    }
    
    return {
      success: true,
      response: response.data.response,
      intent: response.data.intent,
      message: response.data.message,
    };
  } catch (error) {
    // Handle API errors
    if (error.response?.data?.message) {
      throw new Error(error.response.data.message);
    }
    if (error.message) {
      throw error;
    }
    throw new Error('Failed to generate response from conversation');
  }
};

/**
 * Generate button response from scenario (RIGHT SIDE)
 * @param {string} buttonIntent - Button intent name (e.g., 'morning_flirt', 'sensual')
 * @returns {Promise} Response with: success, response, theme
 */
export const generateButtonResponse = async (buttonIntent) => {
  // Validate input
  if (!buttonIntent || !buttonIntent.trim()) {
    throw new Error('Button intent is required');
  }
  
  const validButtons = [
    'dead',
    'new_match',
    'morning_flirt',
    'deep_talk',
    'dinner_talk',
    'sensual',
    'meeting_divert',
    'insist',
    'public_talks',
    'bedroom_questions',
    'positions',
    'lyrical_romance',
    'vulnerability'
  ];
  
  if (!validButtons.includes(buttonIntent)) {
    throw new Error(`Invalid button intent: ${buttonIntent}`);
  }
  
  try {
    const response = await apiClient.post('/chat/generate-button/', {
      button_intent: buttonIntent,
    });
    
    // Verify response structure
    if (!response.data.success) {
      throw new Error(response.data.message || 'Failed to generate response');
    }
    
    return {
      success: true,
      response: response.data.response,
      theme: response.data.theme,
      message: response.data.message,
    };
  } catch (error) {
    // Handle API errors
    if (error.response?.data?.message) {
      throw new Error(error.response.data.message);
    }
    if (error.message) {
      throw error;
    }
    throw new Error(`Failed to generate response for button: ${buttonIntent}`);
  }
};

/**
 * Get list of all available button intents
 * @returns {Array} Array of button intent objects with name and description
 */
export const getAvailableButtons = () => {
  return [
    { id: 'dead', label: 'Dead', description: 'Getting her interest back' },
    { id: 'new_match', label: 'New Match', description: 'Just matched, starting' },
    { id: 'morning_flirt', label: 'Morning Flirt', description: 'Morning message' },
    { id: 'deep_talk', label: 'Deep Talk', description: 'Meaningful conversation' },
    { id: 'dinner_talk', label: 'Dinner Talk', description: 'About going to dinner' },
    { id: 'sensual', label: 'Sensual', description: 'Flirty & suggestive' },
    { id: 'meeting_divert', label: 'Meeting Divert', description: 'Change plans to meet' },
    { id: 'insist', label: 'Insist', description: 'Persistence on meeting' },
    { id: 'public_talks', label: 'Public Talks', description: 'General social topics' },
    { id: 'bedroom_questions', label: 'Bedroom Q', description: 'Sexual topics' },
    { id: 'positions', label: 'Positions', description: 'Explicit scenarios' },
    { id: 'lyrical_romance', label: 'Lyrical', description: 'Romantic & poetic' },
    { id: 'vulnerability', label: 'Vulnerability', description: 'Emotional & open' },
  ];
};

export default {
  generateSpecificResponse,
  generateButtonResponse,
  getAvailableButtons,
};
