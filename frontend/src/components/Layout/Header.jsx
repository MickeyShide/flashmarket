import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import { formatDate } from '../../utils/formatters';

export const Header = ({ currentView, setCurrentView, toggleMobileNav, goHome, switchProfileTab }) => {
  const { user, notifications, unreadNotifCount, markNotifRead } = useAuth();
  const { getCartCount } = useCart();
  const [showNotifDrop, setShowNotifDrop] = useState(false);
  const notifRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifDrop(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const rawLabel = user?.full_name || user?.email || '';
  const displayLabel = rawLabel.length > 16 ? rawLabel.slice(0, 16) + '…' : rawLabel;

  return (
    <header className="bg-white border-b border-border-color sticky top-0 z-[100] w-full">
      <div className="max-w-[1280px] mx-auto px-4 md:px-6 py-3 md:py-4 flex items-center justify-between gap-3">
        {/* Left */}
        <div className="flex items-center gap-[8px] md:gap-[12px]">
          <button
            className="md:hidden p-1 flex items-center justify-center cursor-pointer"
            onClick={toggleMobileNav}
            aria-label="Toggle menu"
          >
            <svg className="w-[18px] h-[18px] stroke-black fill-none stroke-2 stroke-linecap-round stroke-linejoin-round" viewBox="0 0 24 24">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
        </div>

        {/* Center - Brand Title */}
        <div className="text-center flex-1 min-w-0 cursor-pointer" onClick={goHome}>
          <h1 className="font-sans font-black text-sm md:text-xl tracking-[1px] md:tracking-[2.5px] uppercase select-none whitespace-nowrap leading-none">
            FLASHMARKET
          </h1>
          <div className="font-mono text-[7.5px] md:text-[8.5px] tracking-[1px] md:tracking-[2px] uppercase text-text-muted mt-1 whitespace-nowrap">
            LIMITED DROPS &amp; RELEASES
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center justify-end gap-2 md:gap-[14px] relative" ref={notifRef}>
          {/* Notifications bell (Desktop) */}
          {user && (
            <div className="hidden md:flex relative">
              <button
                className="p-[4px] flex items-center justify-center cursor-pointer relative"
                onClick={() => setShowNotifDrop(prev => !prev)}
                title="Уведомления"
              >
                <svg className="w-5 h-5 stroke-black fill-none stroke-2 stroke-linecap-round stroke-linejoin-round" viewBox="0 0 24 24">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
                {unreadNotifCount > 0 && (
                  <span className="absolute -top-[3px] -right-[5px] bg-accent-red text-white text-[9px] font-black min-w-[16px] h-[16px] rounded-full flex items-center justify-center px-1">
                    {unreadNotifCount > 9 ? '9+' : unreadNotifCount}
                  </span>
                )}
              </button>

              {/* Notification Dropdown */}
              {showNotifDrop && (
                <div className="absolute top-full right-[40px] w-[320px] bg-white border border-border-color rounded-md shadow-xl flex flex-col z-[200]">
                  <div className="p-3 text-[11px] font-black tracking-wider uppercase border-b border-border-color flex justify-between items-center">
                    <span>Уведомления</span>
                    <span className="text-[10px] text-text-muted font-normal">{notifications.length} всего</span>
                  </div>
                  <div className="max-h-[280px] overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="p-4 text-center text-text-muted text-[11px]">Нет уведомлений</div>
                    ) : (
                      notifications.slice(0, 5).map(n => (
                        <div
                          key={n.id}
                          className={`p-3 border-b border-border-color cursor-pointer hover:bg-gray-50 transition-colors ${n.status === 'PENDING' ? 'bg-[#FFFDE7]' : ''}`}
                          onClick={() => {
                            if (n.status === 'PENDING') markNotifRead(n.id);
                          }}
                        >
                          <div className="font-extrabold text-[11px]">{n.subject}</div>
                          <div className="text-[10.5px] text-gray-700 mt-0.5">{n.body}</div>
                          <div className="text-[9.5px] text-text-muted mt-1">{formatDate(n.created_at)}</div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="p-2.5 text-center border-t border-border-color text-[10.5px] font-extrabold uppercase">
                    <button
                      className="hover:text-accent-red cursor-pointer"
                      onClick={() => {
                        setShowNotifDrop(false);
                        setCurrentView('auth');
                        if (switchProfileTab) switchProfileTab('notifications');
                      }}
                    >
                      Все уведомления →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* User Auth Button */}
          <button
            className="p-[4px] flex items-center justify-center cursor-pointer"
            onClick={() => setCurrentView('auth')}
            title={user ? rawLabel : 'Войти'}
          >
            {user ? (
              <span className="max-w-[65px] md:max-w-[110px] truncate inline-block align-middle text-[10.5px] font-black tracking-wider uppercase">
                {displayLabel}
              </span>
            ) : (
              <svg className="w-[18px] md:w-[20px] h-[18px] md:h-[20px] stroke-black fill-none stroke-2 stroke-linecap-round stroke-linejoin-round" viewBox="0 0 24 24">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            )}
          </button>

          {/* Developer Hub Link Button */}
          <button
            onClick={() => {
              setCurrentView('dev');
              if (window.location.pathname !== '/dev') {
                window.history.pushState({}, '', '/dev');
              }
            }}
            className="px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider bg-black text-[#BFF532] hover:bg-zinc-800 rounded transition-colors flex items-center gap-1 border border-black cursor-pointer"
            title="Developer Hub API Explorer (/dev)"
          >
            <span>DEV</span>
            <span className="hidden md:inline">HUB</span>
          </button>

          {/* Cart Icon Button */}
          <button
            className="p-[4px] flex items-center justify-center cursor-pointer relative"
            onClick={() => setCurrentView('cart')}
            title="Корзина"
          >
            <svg className="w-[18px] md:w-[20px] h-[18px] md:h-[20px] stroke-black fill-none stroke-2 stroke-linecap-round stroke-linejoin-round" viewBox="0 0 24 24">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <path d="M16 10a4 4 0 0 1-8 0"></path>
            </svg>
            <span className="absolute -top-[3px] -right-[5px] bg-black text-white text-[9px] font-black w-[16px] h-[16px] rounded-full flex items-center justify-center">
              {getCartCount()}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
};
