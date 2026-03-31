/**
 * Location Service
 * Handles all API calls related to location search
 * Uses GeoNames API via backend to find cities 45 mins away
 */

import apiClient from './apiClient';

/**
 * Search for cities within 45 minutes of a given state
 * @param {string} state - Name of the state (e.g., 'California')
 * @returns {Promise} List of cities with their details
 */
export const searchCitiesNearState = async (city, state) => {
  try {
    const response = await apiClient.get('/locations/', {
      params: {
        city: city,
        state: state,
      },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};
