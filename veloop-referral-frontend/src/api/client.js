// ============================================================
// Thin API client. Every referral value rendered by this app comes from here.
// No reward maths, no counters and no eligibility logic lives on the client.
// ============================================================
import { deviceHeaders, saveDeviceToken } from './device';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '');
const TOKEN_KEY = 'veloop_access_token';

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export class ApiError extends Error {
  constructor({ code, message, status, maskedEmail, details }) {
    super(message || 'Request failed');
    this.code = code || 'INTERNAL_ERROR';
    this.status = status;
    this.maskedEmail = maskedEmail || null;
    this.details = details || null;
  }
}
  }
}

export async function apiRequest(path, { method = 'GET', body, auth = true, idempotencyKey } = {}) {
  const headers = { 'Content-Type': 'application/json', ...deviceHeaders() };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError({ code: 'NETWORK_ERROR', message: 'Could not reach VELoop servers.' });
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok || payload?.success === false) {
    throw new ApiError({
      code: payload?.code,
      message: payload?.message,
      status: response.status,
      maskedEmail: payload?.maskedEmail,
      details: payload?.details,
    });
  }

  if (payload?.data?.deviceToken) saveDeviceToken(payload.data.deviceToken);
  return payload?.data ?? payload;
}
