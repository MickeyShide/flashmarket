import { ACCESS_TOKEN_KEY } from '../config/constants';
import { getCsrfToken } from '../utils/formatters';

let isRefreshingToken = false;
let onSessionExpiredCallback = null;

export function setSessionExpiredCallback(cb) {
  onSessionExpiredCallback = cb;
}

export async function api(path, options = {}, tokenOverride = null) {
  const token = tokenOverride !== null ? tokenOverride : localStorage.getItem(ACCESS_TOKEN_KEY);
  const headers = { 'Accept': 'application/json', ...(options.headers || {}) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  let res = await fetch(path, { ...options, headers, credentials: 'include' });

  // Task 8: Transparent Refresh Token on 401
  if (res.status === 401 && !path.includes('/auth/login') && !path.includes('/auth/refresh')) {
    if (!isRefreshingToken) {
      isRefreshingToken = true;
      try {
        const refreshHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
        const currentCsrf = getCsrfToken();
        if (currentCsrf) {
          refreshHeaders['X-CSRF-Token'] = currentCsrf;
        }
        const refreshRes = await fetch('/auth/refresh', {
          method: 'POST',
          headers: refreshHeaders,
          body: JSON.stringify({}),
          credentials: 'include'
        });

        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          const newToken = refreshData.tokens?.access_token || refreshData.access_token;
          if (newToken) {
            localStorage.setItem(ACCESS_TOKEN_KEY, newToken);
            isRefreshingToken = false;
            headers['Authorization'] = `Bearer ${newToken}`;
            return await fetch(path, { ...options, headers, credentials: 'include' });
          }
        }
      } catch (err) {
        console.warn('Token refresh error:', err);
      }
      isRefreshingToken = false;
    }

    localStorage.removeItem(ACCESS_TOKEN_KEY);
    if (onSessionExpiredCallback) {
      onSessionExpiredCallback();
    }
    throw new Error('Сессия истекла. Войдите снова.');
  }

  return res;
}

export async function apiJson(path, options = {}, tokenOverride = null) {
  const res = await api(path, options, tokenOverride);
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    let msg;
    if (res.status === 403) {
      if (data.detail === "Valid refresh cookie and CSRF token required") {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        if (onSessionExpiredCallback) onSessionExpiredCallback();
        msg = 'Сессия истекла. Войдите снова.';
      } else {
        msg = 'Нет доступа';
      }
    } else if (res.status === 404) {
      msg = data.detail || data.error?.message || 'Не найдено';
    } else if (res.status === 422) {
      if (Array.isArray(data.detail)) {
        msg = data.detail.map(d => d.msg || d.message || JSON.stringify(d)).join('; ');
      } else {
        msg = data.detail || data.error?.message || 'Ошибка валидации';
      }
    } else if (res.status >= 500) {
      msg = 'Ошибка сервера. Попробуйте позже.';
    } else {
      msg = data.detail || data.error?.message || data.message || `${res.status} ${res.statusText}`;
    }
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}
