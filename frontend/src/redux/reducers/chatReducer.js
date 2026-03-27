/**
 * Chat Redux Reducer
 * 
 * Manages chat state:
 * - response: The AI-generated response text
 * - isUnique: Boolean indicating if response is unique or rephrased
 * - loading: Boolean indicating if a request is in progress
 * - error: Error message if request fails
 * 
 * Actions handled:
 * - GET_CHAT_RESPONSE_REQUEST
 * - GET_CHAT_RESPONSE_SUCCESS
 * - GET_CHAT_RESPONSE_FAILURE
 * - CLEAR_CHAT_RESPONSE
 */

import {
  GET_CHAT_RESPONSE_REQUEST,
  GET_CHAT_RESPONSE_SUCCESS,
  GET_CHAT_RESPONSE_FAILURE,
  CLEAR_CHAT_RESPONSE,
} from '../actions/chatActions';

// Initial state
const initialState = {
  response: '',
  isUnique: null,
  loading: false,
  error: null,
};

/**
 * Chat reducer
 * 
 * @param {Object} state - Current chat state
 * @param {Object} action - Redux action
 * @returns {Object} Updated chat state
 */
const chatReducer = (state = initialState, action) => {
  switch (action.type) {
    case GET_CHAT_RESPONSE_REQUEST:
      // Request started, set loading to true
      return {
        ...state,
        loading: true,
        error: null,
      };

    case GET_CHAT_RESPONSE_SUCCESS:
      // Request succeeded, store response and uniqueness status
      return {
        ...state,
        response: action.payload.response,
        isUnique: action.payload.isUnique,
        loading: false,
        error: null,
      };

    case GET_CHAT_RESPONSE_FAILURE:
      // Request failed, store error message
      return {
        ...state,
        loading: false,
        error: action.payload,
      };

    case CLEAR_CHAT_RESPONSE:
      // Clear response and reset to initial state
      return initialState;

    default:
      return state;
  }
};

export default chatReducer;
