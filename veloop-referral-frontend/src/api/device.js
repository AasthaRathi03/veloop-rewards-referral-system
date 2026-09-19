// ============================================================
// Device signals + signed device token handling.
// We collect only coarse, non-personal signals. The BACKEND turns them into
// an HMAC ("device hash"); the raw values are never used for anything else.
// Deliberately excluded: user agent / browser name, so that switching
// Chrome -> Firefox -> Incognito does not create a "new" device.
// ============================================================

const DEVICE_TOKEN_KEY = 'veloop_device_token';

function canvasHint() {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return '';
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('veloop', 2, 2);
    const data = canvas.toDataURL();
    let hash = 0;
    for (let i = 0; i < data.length; i += 1) {
      hash = (hash * 31 + data.charCodeAt(i)) | 0;
    }
    return String(hash);
  } catch {
    return '';
  }
}

export function collectDeviceSignals() {
  const nav = typeof navigator === 'undefined' ? {} : navigator;
  const scr = typeof screen === 'undefined' ? {} : screen;
  return {
    platform: nav.platform || '',
    screen: `${scr.width || 0}x${scr.height || 0}x${scr.colorDepth || 0}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    language: (nav.language || '').slice(0, 5),
    hardware: `${nav.hardwareConcurrency || 0}c/${nav.deviceMemory || 0}g`,
    canvasHint: canvasHint(),
  };
}

function base64Url(value) {
  return btoa(unescape(encodeURIComponent(value)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

export function deviceHeaders() {
  const headers = { 'X-Device-Signals': base64Url(JSON.stringify(collectDeviceSignals())) };
  const token = getDeviceToken();
  if (token) headers['X-Device-Token'] = token;
  return headers;
}

export function getDeviceToken() {
  try {
    return localStorage.getItem(DEVICE_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function saveDeviceToken(token) {
  if (!token) return;
  try {
    localStorage.setItem(DEVICE_TOKEN_KEY, token);
  } catch {
    /* storage blocked - the backend still has its httpOnly cookie + fingerprint */
  }
}
