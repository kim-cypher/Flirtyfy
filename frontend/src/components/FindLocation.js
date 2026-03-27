/**
 * FindLocation Component
 * 
 * Allows users to search for cities exactly 45 minutes away from a given state
 * Features:
 * - Search by US state name
 * - Display cities with:
 *   - Distance in kilometers
 *   - Population
 *   - Coordinates
 * - Show results in sorted order (closest first)
 * - Mobile-friendly results display
 */

import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../redux/actions/authActions';
import { searchCitiesNearState } from '../services/locationService';
import './FindLocation.css';

const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
  'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
  'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
  'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
  'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
  'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
  'Wisconsin', 'Wyoming'
];

function FindLocation() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector(state => state.auth);

  // State management
  const [selectedState, setSelectedState] = useState('');
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);
  const [sortBy, setSortBy] = useState('distance'); // distance or population

  /**
   * Handle logout
   */
  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  /**
   * Navigate to Chat page
   */
  const handleGoToChat = () => {
    navigate('/');
  };

  /**
   * Navigate to Dashboard
   */
  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  /**
   * Search for cities near the selected state
   */
  const handleSearch = async () => {
    if (!selectedState.trim()) {
      setError('Please select a state');
      return;
    }

    setLoading(true);
    setError('');
    setCities([]);
    setSearched(true);

    try {
      const result = await searchCitiesNearState(selectedState);

      if (result.success) {
        // Sort results based on selected sort method
        let sortedCities = [...result.cities];
        if (sortBy === 'distance') {
          sortedCities.sort((a, b) => a.distance - b.distance);
        } else if (sortBy === 'population') {
          sortedCities.sort((a, b) => (b.population || 0) - (a.population || 0));
        }

        setCities(sortedCities);

        if (sortedCities.length === 0) {
          setError(
            'No cities found within 45 minutes of ' + selectedState +
            '. This might be a rural state or geographic boundary issue.'
          );
        }
      } else {
        setError(result.message || 'Failed to search cities');
      }
    } catch (err) {
      setError(
        err.message || 'Error: Could not connect to the server. Please check your internet connection.'
      );
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle sorting changes
   */
  const handleSortChange = (e) => {
    const newSortBy = e.target.value;
    setSortBy(newSortBy);

    // Re-sort the current results
    let sortedCities = [...cities];
    if (newSortBy === 'distance') {
      sortedCities.sort((a, b) => a.distance - b.distance);
    } else if (newSortBy === 'population') {
      sortedCities.sort((a, b) => (b.population || 0) - (a.population || 0));
    }
    setCities(sortedCities);
  };

  /**
   * Format distance for display
   */
  const formatDistance = (km) => {
    return (km / 1.609).toFixed(1); // Convert km to miles
  };

  /**
   * Format population with commas
   */
  const formatPopulation = (pop) => {
    if (!pop) return 'N/A';
    return pop.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  };

  return (
    <div className="location-container">
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="nav-left">
          <h2>📍 Find Location</h2>
        </div>
        <div className="nav-center">
          <button className="nav-btn" onClick={handleGoToChat}>
            💬 Chat
          </button>
          <button className="nav-btn active">Find Location</button>
          <button className="nav-btn" onClick={handleGoToDashboard}>
            ⚙️ Profile
          </button>
        </div>
        <div className="nav-right">
          <span className="user-info">Welcome, {user?.username}!</span>
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className="location-content">
        <div className="location-header">
          <h1>Find Cities 45 Minutes Away</h1>
          <p>Select a US state to discover cities within approximately 45 minutes</p>
        </div>

        {/* Search Section */}
        <div className="search-section">
          <div className="search-card">
            <h3>🔍 Select State</h3>
            <p className="section-description">
              Choose a state to find all cities within 45 minutes (approximately 45km radius)
            </p>

            <div className="search-form">
              <select
                className="state-select"
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                disabled={loading}
              >
                <option value="">-- Select a State --</option>
                {US_STATES.map((state) => (
                  <option key={state} value={state}>
                    {state}
                  </option>
                ))}
              </select>

              <button
                className="btn-search"
                onClick={handleSearch}
                disabled={loading || !selectedState}
              >
                {loading ? '⏳ Searching...' : '🔍 Search'}
              </button>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <span>❌ {error}</span>
          </div>
        )}

        {/* Results Section */}
        {searched && cities.length > 0 && (
          <div className="results-section">
            <div className="results-header">
              <h3>📊 Results for {selectedState}</h3>
              <div className="results-info">
                <span className="result-count">
                  Found <strong>{cities.length}</strong> {cities.length === 1 ? 'city' : 'cities'}
                </span>
                <select className="sort-select" value={sortBy} onChange={handleSortChange}>
                  <option value="distance">📍 Sort by Distance</option>
                  <option value="population">👥 Sort by Population</option>
                </select>
              </div>
            </div>

            {/* Results Table View */}
            <div className="results-table-wrapper">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>City Name</th>
                    <th>Distance</th>
                    <th>Population</th>
                    <th>Coordinates</th>
                  </tr>
                </thead>
                <tbody>
                  {cities.map((city, index) => (
                    <tr key={index} className="city-row">
                      <td className="city-name">
                        <span className="city-number">{index + 1}</span>
                        <span className="city-title">{city.name}</span>
                      </td>
                      <td className="city-distance">
                        {city.distance.toFixed(1)} km
                        <span className="distance-miles">
                          ({formatDistance(city.distance)} mi)
                        </span>
                      </td>
                      <td className="city-population">
                        {formatPopulation(city.population)}
                      </td>
                      <td className="city-coords">
                        <span className="coords-tooltip">
                          {city.latitude.toFixed(4)}, {city.longitude.toFixed(4)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Results Card View (Mobile) */}
            <div className="results-cards">
              {cities.map((city, index) => (
                <div key={index} className="result-card">
                  <div className="card-header">
                    <span className="card-number">#{index + 1}</span>
                    <h4 className="card-title">{city.name}</h4>
                  </div>
                  <div className="card-body">
                    <div className="card-item">
                      <span className="card-label">Distance:</span>
                      <span className="card-value">
                        {city.distance.toFixed(1)} km ({formatDistance(city.distance)} mi)
                      </span>
                    </div>
                    <div className="card-item">
                      <span className="card-label">Population:</span>
                      <span className="card-value">{formatPopulation(city.population)}</span>
                    </div>
                    <div className="card-item">
                      <span className="card-label">Coordinates:</span>
                      <span className="card-value">
                        {city.latitude.toFixed(4)}, {city.longitude.toFixed(4)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {searched && cities.length === 0 && !error && (
          <div className="empty-state">
            <p>No cities found. Try another state.</p>
          </div>
        )}

        {!searched && (
          <div className="info-section">
            <div className="info-card">
              <h3>💡 How It Works</h3>
              <ul className="info-list">
                <li>
                  <strong>Select a US state</strong> from the dropdown above
                </li>
                <li>
                  <strong>Click Search</strong> to find all cities within 45 minutes
                  (approximately 45-75km radius)
                </li>
                <li>
                  <strong>View results</strong> with distance, population, and coordinates
                </li>
                <li>
                  <strong>Sort results</strong> by distance (closest first) or population
                  (largest first)
                </li>
              </ul>
            </div>

            <div className="info-card">
              <h3>📌 About the Search</h3>
              <ul className="info-list">
                <li>
                  <strong>Data Source:</strong> GeoNames.org - Global geographic database
                </li>
                <li>
                  <strong>Search Radius:</strong> Approximately 45-75km from state center
                </li>
                <li>
                  <strong>Accuracy:</strong> Results based on straight-line distance (as-the-crow-flies)
                </li>
                <li>
                  <strong>Note:</strong> Some states may have limited nearby cities due to geography
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default FindLocation;
