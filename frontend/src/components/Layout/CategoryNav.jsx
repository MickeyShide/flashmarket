import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { flattenCategories } from '../../utils/formatters';
import { prefetchCategories, prefetchProfile, prefetchAdmin } from '../../services/prefetch';
import { apiJson } from '../../services/api';

export const CategoryNav = ({
  categoriesData,
  activeCategoryId,
  activeBrandId,
  filterCategory,
  mobileNavOpen,
  closeMobileNav,
  currentView,
  setCurrentView,
  switchProfileTab
}) => {
  const { user, unreadNotifCount } = useAuth();

  return (
    <nav className={`border-t border-border-color bg-white w-full transition-all duration-250 ${mobileNavOpen ? 'max-h-[500px] border-t' : 'max-h-0 md:max-h-none overflow-hidden md:overflow-visible border-t-0 md:border-t'}`}>
      <div className="max-w-[1280px] mx-auto flex flex-col md:flex-row items-start md:items-center justify-center gap-3.5 md:gap-8 px-4 md:px-6 py-3.5 md:py-3 whitespace-nowrap">
        {/* ВСЕ ТОВАРЫ */}
        <button
          className={`text-[12px] md:text-[11.5px] font-extrabold tracking-[1.5px] uppercase cursor-pointer py-1 relative w-full md:w-auto text-left md:text-center ${currentView === 'catalog' && !activeCategoryId && !activeBrandId ? 'text-black' : 'text-text-main'}`}
          onClick={() => {
            filterCategory(null);
            setCurrentView('catalog');
            closeMobileNav();
          }}
        >
          ВСЕ ТОВАРЫ
          {currentView === 'catalog' && !activeCategoryId && !activeBrandId && (
            <span className="hidden md:block absolute -bottom-[2px] left-0 right-0 h-[2px] bg-black"></span>
          )}
        </button>

        {/* КАТЕГОРИИ */}
        <button
          className={`text-[12px] md:text-[11.5px] font-extrabold tracking-[1.5px] uppercase cursor-pointer py-1 relative w-full md:w-auto text-left md:text-center ${currentView === 'categories' || activeCategoryId ? 'text-black' : 'text-text-main'}`}
          onClick={() => {
            setCurrentView('categories');
            closeMobileNav();
          }}
          onMouseEnter={() => prefetchCategories(apiJson)}
          onFocus={() => prefetchCategories(apiJson)}
        >
          КАТЕГОРИИ
          {(currentView === 'categories' || activeCategoryId) && (
            <span className="hidden md:block absolute -bottom-[2px] left-0 right-0 h-[2px] bg-black"></span>
          )}
        </button>

        {/* ДРОПЫ */}

        {/* ИЗБРАННОЕ */}
        <button
          className="text-[12px] md:text-[11.5px] font-extrabold tracking-[1.5px] uppercase cursor-pointer py-1 w-full md:w-auto text-left md:text-center"
          onClick={() => {
            setCurrentView('auth');
            if (switchProfileTab) switchProfileTab('wishlist');
            closeMobileNav();
          }}
          onMouseEnter={() => prefetchProfile()}
          onFocus={() => prefetchProfile()}
        >
          ИЗБРАННОЕ
        </button>

        {/* Mobile-only Notification link */}
        {user && (
          <button
            className="md:hidden text-[12px] font-extrabold tracking-[1.5px] uppercase cursor-pointer py-1 w-full text-left flex items-center"
            onClick={() => {
              setCurrentView('auth');
              if (switchProfileTab) switchProfileTab('notifications');
              closeMobileNav();
            }}
          >
            УВЕДОМЛЕНИЯ
            {unreadNotifCount > 0 && (
              <span className="inline-flex items-center justify-center bg-red-600 text-white text-[9px] font-black min-w-[16px] h-[16px] rounded-full px-1 ml-1.5">
                {unreadNotifCount > 9 ? '9+' : unreadNotifCount}
              </span>
            )}
          </button>
        )}

        {/* Mobile/Desktop Auth/Profile Link */}
        <button
          className="text-[12px] md:text-[11.5px] font-extrabold tracking-[1.5px] uppercase cursor-pointer py-1 w-full md:w-auto text-left md:text-center"
          onClick={() => {
            setCurrentView('auth');
            closeMobileNav();
          }}
          onMouseEnter={() => prefetchProfile()}
          onFocus={() => prefetchProfile()}
        >
          {user ? 'ПРОФИЛЬ' : 'ВОЙТИ'}
        </button>

        {/* Mobile-only Admin Button */}
        {user?.role === 'ADMIN' && (
          <button
            className="md:hidden text-[12px] font-extrabold tracking-[1.5px] uppercase cursor-pointer py-1 w-full text-left text-red-600 flex items-center gap-2"
            onClick={() => {
              setCurrentView('admin');
              closeMobileNav();
            }}
            onMouseEnter={() => prefetchAdmin()}
            onFocus={() => prefetchAdmin()}
          >
            <span className="px-1.5 py-0.5 text-[9px] font-mono font-black bg-red-600 text-white rounded">ADMIN</span>
            АДМИН ПАНЕЛЬ
          </button>
        )}
      </div>
    </nav>
  );
};
