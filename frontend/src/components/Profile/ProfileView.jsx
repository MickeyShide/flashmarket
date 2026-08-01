import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { formatDate } from '../../utils/formatters';
import { uploadMediaAsset } from '../../services/media';
import { AuthForms } from './AuthForms';
import { OrdersTab } from './OrdersTab';
import { NotificationsTab } from './NotificationsTab';
import { WishlistView } from '../Wishlist/WishlistView';

export const ProfileView = ({ activeTab = 'profile', setActiveTab, onSelectOrder, onOpenProduct, onBack }) => {
  const { user, userAvatar, sessions, logout, closeSession, updateAvatarUrl } = useAuth();
  const { triggerToast } = useToast();
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  if (!user) {
    return (
      <div className="max-w-[1040px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад в каталог
        </button>
        <AuthForms />
      </div>
    );
  }

  const initial = (user.full_name || user.email || 'U').charAt(0).toUpperCase();
  const roleLabel = user.role === 'CUSTOMER' ? 'ПОКУПАТЕЛЬ' : (user.role === 'ADMIN' ? 'АДМИНИСТРАТОР' : user.role);
  const activeSessions = (sessions || []).filter(s => (s.active !== false) && !s.revoked_at);

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      triggerToast('Выберите файл изображения (PNG, JPG, WEBP)', true);
      return;
    }

    setUploadingAvatar(true);
    try {
      const asset = await uploadMediaAsset(file, 'user_avatar', 'user', user.id);
      if (asset?.public_url) {
        updateAvatarUrl(asset.public_url);
        triggerToast('Аватар успешно обновлен!');
      }
    } catch (err) {
      triggerToast(err.message || 'Ошибка загрузки аватара', true);
    } finally {
      setUploadingAvatar(false);
    }
  };

  return (
    <div className="max-w-[1040px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
        ← Назад в каталог
      </button>

      {/* Main Profile Header Banner */}
      <div className="bg-black text-white rounded-lg p-6 mb-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {/* Avatar Upload Container */}
          <div className="relative group cursor-pointer">
            <div className="w-16 h-16 rounded-full bg-white/15 overflow-hidden flex items-center justify-center text-xl font-black border-2 border-white/30 relative">
              {userAvatar ? (
                <img src={userAvatar} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                <span>{initial}</span>
              )}
              {uploadingAvatar && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center text-[9px] font-bold">
                  ...
                </div>
              )}
            </div>
            <label className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center text-[9px] font-bold uppercase tracking-wider text-white transition-opacity cursor-pointer">
              Изменить
              <input
                type="file"
                accept="image/*"
                className="hidden"
                disabled={uploadingAvatar}
                onChange={handleAvatarChange}
              />
            </label>
          </div>

          <div>
            <h2 className="text-lg font-black uppercase tracking-wide">
              {user.full_name || 'Пользователь'}
            </h2>
            <div className="font-mono text-[10px] text-accent-lime font-bold uppercase tracking-wider mt-0.5">
              {roleLabel}
            </div>
          </div>
        </div>

        <button
          className="bg-white/10 text-white border border-white/20 px-4 py-2 rounded text-[10.5px] font-extrabold uppercase tracking-wider hover:bg-red-600 hover:border-red-600 cursor-pointer transition-colors"
          onClick={() => {
            if (window.confirm('Вы уверены, что хотите выйти?')) {
              logout();
            }
          }}
        >
          ВЫЙТИ ИЗ АККАУНТА
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-border-color mb-6 gap-6 overflow-x-auto no-scrollbar">
        <button
          className={`py-3 text-xs font-black tracking-wider uppercase cursor-pointer whitespace-nowrap relative ${
            activeTab === 'profile' ? 'text-black' : 'text-text-muted hover:text-black'
          }`}
          onClick={() => setActiveTab('profile')}
        >
          ПРОФИЛЬ
          {activeTab === 'profile' && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-black"></span>}
        </button>
        <button
          className={`py-3 text-xs font-black tracking-wider uppercase cursor-pointer whitespace-nowrap relative ${
            activeTab === 'wishlist' ? 'text-black' : 'text-text-muted hover:text-black'
          }`}
          onClick={() => setActiveTab('wishlist')}
        >
          ИЗБРАННОЕ
          {activeTab === 'wishlist' && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-black"></span>}
        </button>
        <button
          className={`py-3 text-xs font-black tracking-wider uppercase cursor-pointer whitespace-nowrap relative ${
            activeTab === 'orders' ? 'text-black' : 'text-text-muted hover:text-black'
          }`}
          onClick={() => setActiveTab('orders')}
        >
          МОИ ЗАКАЗЫ
          {activeTab === 'orders' && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-black"></span>}
        </button>
        <button
          className={`py-3 text-xs font-black tracking-wider uppercase cursor-pointer whitespace-nowrap relative ${
            activeTab === 'notifications' ? 'text-black' : 'text-text-muted hover:text-black'
          }`}
          onClick={() => setActiveTab('notifications')}
        >
          УВЕДОМЛЕНИЯ
          {activeTab === 'notifications' && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-black"></span>}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          {/* User Fields Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-white border border-border-color rounded-lg p-4">
              <div className="text-[10px] font-extrabold uppercase text-text-muted mb-1">Email</div>
              <div className="text-xs font-bold text-black">{user.email}</div>
            </div>

            <div className="bg-white border border-border-color rounded-lg p-4">
              <div className="text-[10px] font-extrabold uppercase text-text-muted mb-1">Имя</div>
              <div className="text-xs font-bold text-black">{user.full_name || 'Не указано'}</div>
            </div>

            <div className="bg-white border border-border-color rounded-lg p-4">
              <div className="text-[10px] font-extrabold uppercase text-text-muted mb-1">Статус аккаунта</div>
              <div>
                {user.is_active ? (
                  <span className="text-[10px] font-extrabold bg-green-100 text-green-800 px-2 py-0.5 rounded uppercase">Активен</span>
                ) : (
                  <span className="text-[10px] font-extrabold text-red-600 uppercase">Заблокирован</span>
                )}
              </div>
            </div>

            <div className="bg-white border border-border-color rounded-lg p-4">
              <div className="text-[10px] font-extrabold uppercase text-text-muted mb-1">Дата регистрации</div>
              <div className="text-xs font-bold text-black">{formatDate(user.created_at)}</div>
            </div>

            <div className="bg-white border border-border-color rounded-lg p-4 sm:col-span-2">
              <div className="text-[10px] font-extrabold uppercase text-text-muted mb-1">ID пользователя</div>
              <code className="text-[11px] font-mono bg-gray-100 px-2 py-1 rounded text-gray-800 block truncate">{user.id}</code>
            </div>
          </div>

          {/* Active Sessions Section */}
          <div className="bg-white border border-border-color rounded-lg p-6">
            <h3 className="text-sm font-black uppercase tracking-wide mb-4">Активные сессии</h3>
            {activeSessions.length === 0 ? (
              <div className="text-text-muted text-xs text-center py-4">Нет активных сессий</div>
            ) : (
              <div className="space-y-3">
                {activeSessions.map(s => (
                  <div key={s.id} className="p-3 bg-gray-50 border border-border-color rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                    <div>
                      <span className="font-bold">{s.user_agent || 'Unknown'}</span> · {s.ip_address || '-'} · {formatDate(s.created_at)}
                      {s.current && (
                        <span className="ml-2 text-[9px] font-black bg-black text-white px-1.5 py-0.5 rounded">ТЕКУЩАЯ</span>
                      )}
                    </div>
                    <button
                      className="bg-black text-white text-[10px] font-bold px-2.5 py-1 rounded uppercase hover:bg-gray-800 self-start sm:self-center"
                      onClick={() => closeSession(s.id)}
                    >
                      ЗАКРЫТЬ
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'wishlist' && (
        <WishlistView
          onOpenProduct={onOpenProduct || (() => {})}
          onGoToCatalog={onBack}
        />
      )}

      {activeTab === 'orders' && <OrdersTab onSelectOrder={onSelectOrder} />}
      {activeTab === 'notifications' && <NotificationsTab />}
    </div>
  );
};
