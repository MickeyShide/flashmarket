import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { ACCESS_TOKEN_KEY } from '../config/constants';
import { apiJson, setSessionExpiredCallback } from '../services/api';
import { useToast } from './ToastContext';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const { triggerToast } = useToast();
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadNotifCount, setUnreadNotifCount] = useState(0);

  const handleSessionExpired = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setSessions([]);
    setNotifications([]);
    setUnreadNotifCount(0);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    triggerToast('Сессия истекла. Войдите снова.', true);
  }, [triggerToast]);

  useEffect(() => {
    setSessionExpiredCallback(handleSessionExpired);
  }, [handleSessionExpired]);

  const loadProfile = useCallback(async () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) return;
    try {
      const userData = await apiJson('/users/me');
      setUser(userData);
      const sessionData = await apiJson('/sessions');
      setSessions(sessionData || []);
    } catch (err) {
      console.error('profile load failed', err);
    }
  }, []);

  const loadNotifications = useCallback(async () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token || !user) return;
    try {
      const data = await apiJson(`/api/v1/notifications/users/${user.id}`);
      const notifs = data.items || [];
      setNotifications(notifs);
      const unread = notifs.filter(n => n.status === 'PENDING');
      setUnreadNotifCount(unread.length);
    } catch (err) {
      console.warn('loadNotifications error:', err);
    }
  }, [user]);

  useEffect(() => {
    if (accessToken) {
      loadProfile();
    } else {
      setUser(null);
      setSessions([]);
      setNotifications([]);
      setUnreadNotifCount(0);
    }
  }, [accessToken, loadProfile]);

  useEffect(() => {
    if (user?.id) {
      loadNotifications();
    }
  }, [user?.id, loadNotifications]);

  const login = async (email, password) => {
    const data = await apiJson('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    setAccessToken(data.tokens.access_token);
    setUser(data.user);
    localStorage.setItem(ACCESS_TOKEN_KEY, data.tokens.access_token);
    triggerToast(`Добро пожаловать, ${data.user.full_name || data.user.email}!`);
    return data;
  };

  const register = async (email, password, full_name) => {
    const body = { email, password };
    if (full_name) body.full_name = full_name;
    const data = await apiJson('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    setAccessToken(data.tokens.access_token);
    setUser(data.user);
    localStorage.setItem(ACCESS_TOKEN_KEY, data.tokens.access_token);
    triggerToast(`Добро пожаловать, ${data.user.full_name || data.user.email}!`);
    return data;
  };

  const logout = async () => {
    try {
      await apiJson('/auth/logout', { method: 'POST' });
    } catch (e) { }
    setAccessToken(null);
    setUser(null);
    setSessions([]);
    setNotifications([]);
    setUnreadNotifCount(0);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    triggerToast('Вы вышли из аккаунта');
  };

  const closeSession = async (sessionId) => {
    try {
      await apiJson('/sessions/' + sessionId, { method: 'DELETE' });
      triggerToast('Сессия закрыта');
      loadProfile();
    } catch (err) {
      triggerToast('Ошибка: ' + err.message, true);
    }
  };

  const markNotifRead = async (notificationId) => {
    try {
      await apiJson(`/api/v1/notifications/${notificationId}/send`, { method: 'POST' });
      triggerToast('Уведомление отмечено прочитанным');
      loadNotifications();
    } catch (err) {
      loadNotifications();
    }
  };

  return (
    <AuthContext.Provider value={{
      accessToken,
      user,
      sessions,
      notifications,
      unreadNotifCount,
      login,
      register,
      logout,
      closeSession,
      loadProfile,
      loadNotifications,
      markNotifRead
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
