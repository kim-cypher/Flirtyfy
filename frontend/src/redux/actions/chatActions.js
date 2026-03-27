/**
 * Chat Redux Actions
 * 
 * Actions for managing chat-related state:
 * - GET_CHAT_RESPONSE_REQUEST
 * - GET_CHAT_RESPONSE_SUCCESS
 * - GET_CHAT_RESPONSE_FAILURE
 * - CLEAR_CHAT_RESPONSE
 * 
 * Thunk action:
 * - getResponse(conversation) - Fetches AI response from backend
 */

import { generateChatResponse } from '../../services/chatService';

// Action types
export const GET_CHAT_RESPONSE_REQUEST = 'GET_CHAT_RESPONSE_REQUEST';
export const GET_CHAT_RESPONSE_SUCCESS = 'GET_CHAT_RESPONSE_SUCCESS';
export const GET_CHAT_RESPONSE_FAILURE = 'GET_CHAT_RESPONSE_FAILURE';
export const CLEAR_CHAT_RESPONSE = 'CLEAR_CHAT_RESPONSE';

/**
 * Thunk action creator
 * Fetches AI response for a given conversation
 * 
 * @param {string} conversation - The conversation text to analyze
 * @returns {Function} Redux thunk
 */
export const getResponse = (conversation) => async (dispatch) => {
  dispatch({ type: GET_CHAT_RESPONSE_REQUEST });

  try {
    const result = await generateChatResponse(conversation);

    if (result.success) {
      dispatch({
        type: GET_CHAT_RESPONSE_SUCCESS,
        payload: {
          response: result.response,
          isUnique: result.is_unique,
        },
      });
    } else {
      dispatch({
        type: GET_CHAT_RESPONSE_FAILURE,
        payload: result.message || 'Failed to generate response',
      });
    }
  } catch (error) {
    dispatch({
      type: GET_CHAT_RESPONSE_FAILURE,
      payload: error.message || 'Error generating response',
    });
  }
};

/**
 * Clear chat response from state
 * Resets response, isUnique, and error to default values
 */
export const clearChatResponse = () => ({
  type: CLEAR_CHAT_RESPONSE,
});
