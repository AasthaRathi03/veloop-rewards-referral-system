// All referral endpoints in one place.
import { apiRequest, setToken } from './client';

export const getReferralDashboard = () => apiRequest('/referrals/me');

export const getReferrals = ({ page = 1, limit = 10, status } = {}) => {
  const params = new URLSearchParams({ page, limit });
  if (status && status !== 'all') params.set('status', status);
  return apiRequest(`/referrals?${params.toString()}`);
};

export const getSpamReferrals = () => apiRequest('/referrals/spam');

export const getReferralProgress = (referralId) => apiRequest(`/referrals/${referralId}/progress`);

export const getRewardHistory = ({ page = 1, limit = 20 } = {}) =>
  apiRequest(`/referrals/rewards/history?page=${page}&limit=${limit}`);

export const getMilestoneConfig = () => apiRequest('/referrals/config/milestones');

export const attributeReferral = (referralCode) =>
  apiRequest('/referrals/attribute', { method: 'POST', body: { referralCode } });

export const trackReferralClick = (referralCode) =>
  apiRequest('/referrals/click', { method: 'POST', body: { referralCode }, auth: false });

export async function login(email, password) {
  const data = await apiRequest('/auth/login', { method: 'POST', body: { email, password }, auth: false });
  setToken(data.accessToken);
  return data;
}

export async function register({ email, password, phone, referralCode }) {
  const data = await apiRequest('/auth/register', {
    method: 'POST',
    body: { email, password, phone, referralCode },
    auth: false,
  });
  setToken(data.accessToken);
  return data;
}

export const logout = () => setToken(null);
