import apiClient from '../../services/apiClient';

export const login = (email, password) => async (dispatch) => {
  dispatch({ type: 'LOGIN_REQUEST' });
  try {
    const response = await apiClient.post('/login/', {
      email,
      password,
    });
    const { token, user } = response.data;
    localStorage.setItem('access_token', token);
    dispatch({
      type: 'LOGIN_SUCCESS',
      payload: { token, user },
    });
    return response.data;
  } catch (error) {
    // Extract error message from various response formats
    let errorMessage = 'Login failed';
    const errorData = error.response?.data;
    
    if (errorData) {
      // Try extracting from various possible error formats
      if (errorData.message) {
        errorMessage = errorData.message;
      } else if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
        errorMessage = errorData.non_field_errors[0];
      } else if (errorData.email && Array.isArray(errorData.email)) {
        errorMessage = errorData.email[0];
      } else if (errorData.password && Array.isArray(errorData.password)) {
        errorMessage = errorData.password[0];
      } else if (errorData.detail) {
        errorMessage = errorData.detail;
      }
    }
    
    dispatch({
      type: 'LOGIN_FAILURE',
      payload: errorMessage,
    });
    throw error;
  }
};

export const register = (username, email, password, confirmPassword, dateOfBirth) => async (dispatch) => {
  dispatch({ type: 'REGISTER_REQUEST' });
  try {
    const response = await apiClient.post('/register/', {
      username,
      email,
      password,
      confirmPassword,
      date_of_birth: dateOfBirth, // Convert camelCase to snake_case for backend
    });
    const { token, user } = response.data;
    localStorage.setItem('access_token', token);
    dispatch({
      type: 'REGISTER_SUCCESS',
      payload: { token, user },
    });
    return response.data;
  } catch (error) {
    // Extract error message from various response formats
    let errorMessage = 'Registration failed';
    const errorData = error.response?.data;
    
    if (errorData) {
      // Try extracting from various possible error formats
      if (errorData.message) {
        errorMessage = errorData.message;
      } else if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
        errorMessage = errorData.non_field_errors[0];
      } else if (errorData.email && Array.isArray(errorData.email)) {
        errorMessage = errorData.email[0];
      } else if (errorData.username && Array.isArray(errorData.username)) {
        errorMessage = errorData.username[0];
      } else if (errorData.password && Array.isArray(errorData.password)) {
        errorMessage = errorData.password[0];
      } else if (errorData.date_of_birth && Array.isArray(errorData.date_of_birth)) {
        errorMessage = errorData.date_of_birth[0];
      } else if (errorData.detail) {
        errorMessage = errorData.detail;
      }
    }
    
    dispatch({
      type: 'REGISTER_FAILURE',
      payload: errorMessage,
    });
    throw error;
  }
};

export const logout = () => (dispatch) => {
  localStorage.removeItem('access_token');
  dispatch({ type: 'LOGOUT' });
};