import apiClient from '../../services/apiClient';

// DRF error shapes vary: {message}, {detail}, {non_field_errors: [...]},
// or {field: [...]} — and some backend ValidationErrors raise a plain
// string per field instead of a list, which earlier code only checked for
// arrays, so those messages silently fell back to a generic "X failed".
// This pulls the first usable message out of whatever shape comes back.
export function extractErrorMessage(errorData, fallback) {
  if (!errorData) return fallback;
  if (typeof errorData === 'string') return errorData;
  if (errorData.message) return errorData.message;
  if (errorData.detail) return errorData.detail;
  for (const key of Object.keys(errorData)) {
    const val = errorData[key];
    if (Array.isArray(val) && val.length) return String(val[0]);
    if (typeof val === 'string' && val) return val;
  }
  return fallback;
}

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
    const errorMessage = extractErrorMessage(error.response?.data, 'Login failed');
    dispatch({
      type: 'LOGIN_FAILURE',
      payload: errorMessage,
    });
    throw error;
  }
};

export const register = (username, email, firstName, password, confirmPassword, dateOfBirth, referralCode = '') => async (dispatch) => {
  dispatch({ type: 'REGISTER_REQUEST' });
  try {
    const response = await apiClient.post('/register/', {
      username,
      email,
      first_name: firstName,
      password,
      confirmPassword,
      date_of_birth: dateOfBirth, // Convert camelCase to snake_case for backend
      referral_code: referralCode,
    });
    const { token, user } = response.data;
    localStorage.setItem('access_token', token);
    dispatch({
      type: 'REGISTER_SUCCESS',
      payload: { token, user },
    });
    return response.data;
  } catch (error) {
    const errorMessage = extractErrorMessage(error.response?.data, 'Registration failed');
    dispatch({
      type: 'REGISTER_FAILURE',
      payload: errorMessage,
    });
    throw error;
  }
};

export const resetPassword = (email, firstName, newPassword, confirmNewPassword) => async (dispatch) => {
  try {
    const response = await apiClient.post('/password-reset/', {
      email,
      first_name: firstName,
      new_password: newPassword,
      confirm_new_password: confirmNewPassword,
    });
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error.response?.data, 'Password reset failed'));
  }
};

export const logout = () => (dispatch) => {
  localStorage.removeItem('access_token');
  dispatch({ type: 'LOGOUT' });
};