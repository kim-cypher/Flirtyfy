/**
 * Chat Service
 * Handles all API calls related to chat functionality
 * Communicates with backend OpenAI integration
 */

import apiClient from './apiClient';

/**
 * Upload chat to async novelty endpoint
 * @param {string} conversation - The conversation text to upload
 * @returns {Promise} Response with upload ID
 */
export const uploadChat = async (conversation) => {
  try {
    const response = await apiClient.post('/novelty/upload/', {
      original_text: conversation,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

/**
 * Poll for latest AI reply for the user
 * @returns {Promise} Array of AI replies
 */
export const fetchLatestReply = async () => {
  try {
    const response = await apiClient.get('/novelty/replies/');
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

/**
 * Generate AI response to a conversation
 * Uploads the conversation and fetches the latest reply
 * @param {string} conversation - The last 10 texts from a conversation
 * @returns {Promise} Response with success, response text, and uniqueness flag
 */
export const generateChatResponse = async (conversation) => {
  try {
    // Step 1: Upload the conversation
    const uploadResponse = await uploadChat(conversation);
    
    if (!uploadResponse.success) {
      return {
        success: false,
        message: uploadResponse.error || 'Failed to upload conversation',
      };
    }

    // Step 2: Fetch the latest reply (which should be the one we just generated)
    const replies = await fetchLatestReply();
    
    if (!replies || replies.length === 0) {
      return {
        success: false,
        message: 'No reply generated',
      };
    }

    // Get the most recent reply
    const latestReply = replies[0];

    return {
      success: true,
      response: latestReply.original_text || latestReply.text,
      is_unique: latestReply.is_unique !== false,
    };
  } catch (error) {
    return {
      success: false,
      message: error.detail || error.message || 'Error generating response',
    };
  }
};
