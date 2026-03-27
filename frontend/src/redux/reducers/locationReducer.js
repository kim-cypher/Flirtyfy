/**
 * Location Redux Reducer
 * 
 * Manages location search state:
 * - cities: Array of city objects with distance, population, coordinates
 * - count: Number of cities found
 * - state: The state that was searched
 * - loading: Boolean indicating if a request is in progress
 * - error: Error message if request fails
 * 
 * Actions handled:
 * - SEARCH_CITIES_REQUEST
 * - SEARCH_CITIES_SUCCESS
 * - SEARCH_CITIES_FAILURE
 * - CLEAR_SEARCH_RESULTS
 */

import {
  SEARCH_CITIES_REQUEST,
  SEARCH_CITIES_SUCCESS,
  SEARCH_CITIES_FAILURE,
  CLEAR_SEARCH_RESULTS,
} from '../actions/locationActions';

// Initial state
const initialState = {
  cities: [],
  count: 0,
  state: '',
  loading: false,
  error: null,
};

/**
 * Location reducer
 * 
 * @param {Object} state - Current location state
 * @param {Object} action - Redux action
 * @returns {Object} Updated location state
 */
const locationReducer = (state = initialState, action) => {
  switch (action.type) {
    case SEARCH_CITIES_REQUEST:
      // Request started, set loading to true
      return {
        ...state,
        loading: true,
        error: null,
      };

    case SEARCH_CITIES_SUCCESS:
      // Request succeeded, store cities and count
      return {
        ...state,
        cities: action.payload.cities,
        count: action.payload.count,
        state: action.payload.state,
        loading: false,
        error: null,
      };

    case SEARCH_CITIES_FAILURE:
      // Request failed, store error message
      return {
        ...state,
        loading: false,
        error: action.payload,
      };

    case CLEAR_SEARCH_RESULTS:
      // Clear search results and reset to initial state
      return initialState;

    default:
      return state;
  }
};

export default locationReducer;
