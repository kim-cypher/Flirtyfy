/**
 * Chat Service
 * Handles all API calls related to chat functionality
 * Communicates with backend OpenAI integration
 */

import apiClient from './apiClient';

/**
 * Generate AI response to a conversation
 * @param {string} conversation - The last 10 texts from a conversation
 * @returns {Promise} Response from OpenAI via backend
 */

// Upload chat to async novelty endpoint
export const uploadChat = async (conversation) => {
  try {
    const response = await apiClient.post('/novelty/upload/', {
      conversation: conversation,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// Poll for latest AI reply for the user
export const fetchLatestReply = async () => {
  try {
    const response = await apiClient.get('/novelty/replies/');
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};
