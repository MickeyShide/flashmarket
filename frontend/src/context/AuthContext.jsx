import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { ACCESS_TOKEN_KEY } from '../config/constants';
import { apiJson, setSessionExpiredCallback } from '../services/api';
import { useToast } from './ToastContext';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const { triggerToast } = useToast();
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [userAvatar, setUserAvatar] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadNotifCount, setUnreadNotifCount] = useState(0);

  const handleSessionExpired = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setUserAvatar(null);
    setSessions([]);
    setNotifications([]);
    setUnreadNotifCount(0);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    triggerToast('Сессия истекла. Войдите снова.', true);
  }, [triggerToast]);

  useEffect(() => {
    setSessionExpiredCallback(handleSessionExpired);
  }, [handleSessionExpired]);

  const loadAvatar = useCallback(async (userId) => {
    if (!userId) return;
    try {
      // Find completed user avatar media asset
      const assetsData = await apiJson(`/api/v1/media/entities/user/${userId}/assets?purpose=user_avatar`).catch(() => []);
      const assets = Array.isArray(assetsData) ? assetsData : (assetsData.items || []);
      const completed = assets.find(a => a.status === 'READY' && a.public_url);
      if (completed) {
        setUserAvatar(completed.public_url);
      }
    } catch (e) {
      console.warn('Failed to load user avatar asset:', e);
    }
  }, []);

  const loadProfile = useCallback(async () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) return;
    try {
      const userData = await apiJson('/users/me');
      setUser(userData);
      loadAvatar(userData.id);
      const sessionData = await apiJson('/sessions');
      setSessions(sessionData || []);
    } catch (err) {
      console.error('profile load failed', err);
    }
  }, [loadAvatar]);

  const loadNotifications = useCallback(async () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token || !user) return;
    try {
      const data = await apiJson(`/api/v1/notifications/users/${user.id}`);
      const notifs = Array.isArray(data) ? data : (data.items || []);
      setNotifications(notifs);
      // Unread count: items missing read_at
      const unread = notifs.filter(n => !n.read_at && n.status !== 'READ');
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
      setUserAvatar(null);
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
    loadAvatar(data.user.id);
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
    setUserAvatar(null);
    setSessions([]);
    setNotifications([]);
    setUnreadNotifCount(0);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    triggerToast('Вы вышли из аккаунта');
  };

  const closeSession = async (sessionId) => {
    const prevSessions = sessions;
    // Optimistic UI update
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    triggerToast('Сессия закрыта');

    try {
      await apiJson('/sessions/' + sessionId, { method: 'DELETE' });
    } catch (err) {
      setSessions(prevSessions);
      triggerToast('Ошибка: ' + err.message, true);
    }
  };

  const markNotifRead = async (notificationId) => {
    const prevNotifications = notifications;
    const prevUnreadCount = unreadNotifCount;

    // Optimistic UI update
    setNotifications(prev => prev.map(n => n.id === notificationId ? { ...n, status: 'READ', read_at: new Date().toISOString() } : n));
    setUnreadNotifCount(prev => Math.max(0, prev - 1));
    triggerToast('Уведомление прочитано');

    try {
      await apiJson(`/api/v1/notifications/${notificationId}/read`, { method: 'POST' });
    } catch (err) {
      setNotifications(prevNotifications);
      setUnreadNotifCount(prevUnreadCount);
    }
  };

  const updateAvatarUrl = (url) => {
    setUserAvatar(url);
  };

  return (
    <AuthContext.Provider value={{
      accessToken,
      user,
      userAvatar,
      sessions,
      notifications,
      unreadNotifCount,
      login,
      register,
      logout,
      closeSession,
      loadProfile,
      loadNotifications,
      markNotifRead,
      updateAvatarUrl
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
