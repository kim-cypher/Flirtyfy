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
    const errorMessage = error.response?.data?.message || 'Login failed';
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
    const errorMessage = error.response?.data?.message || error.response?.data?.date_of_birth?.[0] || 'Registration failed';
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