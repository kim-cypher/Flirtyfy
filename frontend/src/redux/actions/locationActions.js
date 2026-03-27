/**
 * Location Redux Actions
 * 
 * Actions for managing location search state:
 * - SEARCH_CITIES_REQUEST
 * - SEARCH_CITIES_SUCCESS
 * - SEARCH_CITIES_FAILURE
 * - CLEAR_SEARCH_RESULTS
 * 
 * Thunk action:
 * - searchCities(state) - Searches for cities within 45 minutes of a given state
 */

import { searchCitiesNearState } from '../../services/locationService';

// Action types
export const SEARCH_CITIES_REQUEST = 'SEARCH_CITIES_REQUEST';
export const SEARCH_CITIES_SUCCESS = 'SEARCH_CITIES_SUCCESS';
export const SEARCH_CITIES_FAILURE = 'SEARCH_CITIES_FAILURE';
export const CLEAR_SEARCH_RESULTS = 'CLEAR_SEARCH_RESULTS';

/**
 * Thunk action creator
 * Searches for cities within 45 minutes of a given US state
 * 
 * @param {string} state - The US state name to search for
 * @returns {Function} Redux thunk
 */
export const searchCities = (state) => async (dispatch) => {
  dispatch({ type: SEARCH_CITIES_REQUEST });

  try {
    const result = await searchCitiesNearState(state);

    if (result.success) {
      dispatch({
        type: SEARCH_CITIES_SUCCESS,
        payload: {
          cities: result.cities,
          count: result.cities.length,
          state: state,
        },
      });
    } else {
      dispatch({
        type: SEARCH_CITIES_FAILURE,
        payload: result.message || 'Failed to search cities',
      });
    }
  } catch (error) {
    dispatch({
      type: SEARCH_CITIES_FAILURE,
      payload: error.message || 'Error searching cities',
    });
  }
};

/**
 * Clear search results from state
 * Resets cities, count, and error to default values
 */
export const clearSearchResults = () => ({
  type: CLEAR_SEARCH_RESULTS,
});
