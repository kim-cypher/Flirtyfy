/**
 * Credits / Referrals / Notifications / Payments API service.
 * Backed by accounts/views.py: CreditsView, NotificationListView,
 * NotificationMarkReadView, InitiatePaymentView, PaymentStatusView.
 */
import apiClient from './apiClient';

export const getCredits = async () => {
  const response = await apiClient.get('/credits/');
  return response.data;
};

export const getNotifications = async () => {
  const response = await apiClient.get('/notifications/');
  return response.data;
};

export const markNotificationRead = async (id) => {
  const response = await apiClient.post('/notifications/mark-read/', { id });
  return response.data;
};

export const markAllNotificationsRead = async () => {
  const response = await apiClient.post('/notifications/mark-read/', { all: true });
  return response.data;
};

export const initiatePayment = async (phoneNumber, plan = 'topup') => {
  const response = await apiClient.post('/payments/initiate/', { phone_number: phoneNumber, plan });
  return response.data;
};

export const getPaymentStatus = async (checkoutRequestId) => {
  const response = await apiClient.get(`/payments/status/${checkoutRequestId}/`);
  return response.data;
};

/** True if an API error response is the "out of clicks" paywall signal (HTTP 402). */
export const isOutOfClicksError = (error) => {
  return error?.response?.status === 402 && error?.response?.data?.out_of_clicks === true;
};
