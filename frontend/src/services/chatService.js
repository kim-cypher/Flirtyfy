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
export const generateChatResponse = async (conversation) => {
  try {
    const response = await apiClient.post('/chat/', {
      conversation: conversation,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};
