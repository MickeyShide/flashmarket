import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

export const AuthForms = () => {
  const { login, register } = useAuth();
  const [activeTab, setActiveTab] = useState('login'); // 'login' | 'register'

  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginSubmitting, setLoginSubmitting] = useState(false);

  // Register form state
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regName, setRegName] = useState('');
  const [regError, setRegError] = useState('');
  const [regSubmitting, setRegSubmitting] = useState(false);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginSubmitting(true);
    try {
      await login(loginEmail, loginPassword);
    } catch (err) {
      setLoginError(err.message);
    } finally {
      setLoginSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setRegError('');
    setRegSubmitting(true);
    try {
      await register(regEmail, regPassword, regName || undefined);
    } catch (err) {
      setRegError(err.message);
    } finally {
      setRegSubmitting(false);
    }
  };

  return (
    <div className="max-w-[420px] mx-auto bg-white border border-border-color rounded-lg p-6 md:p-8 shadow-sm">
      {/* Tabs Header */}
      <div className="flex border-b border-border-color mb-6">
        <button
          className={`flex-1 py-3 text-xs font-black tracking-wider uppercase cursor-pointer text-center relative ${
            activeTab === 'login' ? 'text-black' : 'text-text-muted hover:text-black'
          }`}
          onClick={() => setActiveTab('login')}
        >
          Вход
          {activeTab === 'login' && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-black"></span>}
        </button>
        <button
          className={`flex-1 py-3 text-xs font-black tracking-wider uppercase cursor-pointer text-center relative ${
            activeTab === 'register' ? 'text-black' : 'text-text-muted hover:text-black'
          }`}
          onClick={() => setActiveTab('register')}
        >
          Регистрация
          {activeTab === 'register' && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-black"></span>}
        </button>
      </div>

      {/* Login Form */}
      {activeTab === 'login' ? (
        <form onSubmit={handleLoginSubmit} className="space-y-4">
          {loginError && (
            <div className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 p-3 rounded">
              {loginError}
            </div>
          )}

          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              required
              className="w-full border border-border-color rounded px-3 py-2 text-xs outline-none focus:border-black font-sans"
              placeholder="user@example.com"
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              Пароль
            </label>
            <input
              type="password"
              required
              className="w-full border border-border-color rounded px-3 py-2 text-xs outline-none focus:border-black font-sans"
              placeholder="••••••••"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={loginSubmitting}
            className="w-full bg-black text-white py-3.5 px-4 text-xs font-black tracking-wider uppercase cursor-pointer rounded hover:bg-gray-900 disabled:opacity-50 transition-colors mt-2"
          >
            {loginSubmitting ? 'ВХОД...' : 'ВОЙТИ'}
          </button>
        </form>
      ) : (
        /* Register Form */
        <form onSubmit={handleRegisterSubmit} className="space-y-4">
          {regError && (
            <div className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 p-3 rounded">
              {regError}
            </div>
          )}

          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              Email *
            </label>
            <input
              type="email"
              required
              className="w-full border border-border-color rounded px-3 py-2 text-xs outline-none focus:border-black font-sans"
              placeholder="user@example.com"
              value={regEmail}
              onChange={(e) => setRegEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              Пароль *
            </label>
            <input
              type="password"
              required
              className="w-full border border-border-color rounded px-3 py-2 text-xs outline-none focus:border-black font-sans"
              placeholder="••••••••"
              value={regPassword}
              onChange={(e) => setRegPassword(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-[10.5px] font-extrabold uppercase tracking-wider text-gray-700 mb-1">
              Имя (опционально)
            </label>
            <input
              type="text"
              className="w-full border border-border-color rounded px-3 py-2 text-xs outline-none focus:border-black font-sans"
              placeholder="Иван Иванов"
              value={regName}
              onChange={(e) => setRegName(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={regSubmitting}
            className="w-full bg-black text-white py-3.5 px-4 text-xs font-black tracking-wider uppercase cursor-pointer rounded hover:bg-gray-900 disabled:opacity-50 transition-colors mt-2"
          >
            {regSubmitting ? 'РЕГИСТРАЦИЯ...' : 'ЗАРЕГИСТРИРОВАТЬСЯ'}
          </button>
        </form>
      )}
    </div>
  );
};
