import React, { lazy, Suspense, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { AdminNav } from './AdminNav';

const lazyNamed = (loader, exportName) => lazy(() => loader().then(module => ({ default: module[exportName] })));

const ProductsTab = lazyNamed(() => import('./Catalog/ProductsTab'), 'ProductsTab');
const BrandsTab = lazyNamed(() => import('./Catalog/BrandsTab'), 'BrandsTab');
const CategoriesTab = lazyNamed(() => import('./Catalog/CategoriesTab'), 'CategoriesTab');
const DropsTab = lazyNamed(() => import('./Drops/DropsTab'), 'DropsTab');
const PromocodesTab = lazyNamed(() => import('./Promocodes/PromocodesTab'), 'PromocodesTab');
const MediaTab = lazyNamed(() => import('./Media/MediaTab'), 'MediaTab');
const UsersTab = lazyNamed(() => import('./Users/UsersTab'), 'UsersTab');
const AuditTab = lazyNamed(() => import('./Audit/AuditTab'), 'AuditTab');
const NotificationsAdminTab = lazyNamed(() => import('./Notifications/NotificationsAdminTab'), 'NotificationsAdminTab');

export const AdminView = ({ onBack }) => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('catalog');

  // Guard access for non-admin users
  if (!user || user.role !== 'ADMIN') {
    return (
      <div className="max-w-[800px] mx-auto my-8 px-4 text-center">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад в каталог
        </button>
        <div className="bg-red-50 border border-red-200 text-red-700 p-8 rounded-lg">
          <h2 className="text-lg font-black uppercase mb-2">Доступ запрещен</h2>
          <p className="text-xs">Панель управления доступна только пользователям с ролью АДМИНИСТРАТОР.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1280px] mx-auto my-4 md:my-8 px-3.5 md:px-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <button
          className="text-[11px] font-bold uppercase tracking-wider cursor-pointer text-text-muted hover:text-black flex items-center gap-1 self-start"
          onClick={onBack}
        >
          ← Назад в магазин
        </button>

        <div className="text-[10.5px] md:text-xs font-bold font-mono text-purple-700 uppercase truncate">
          ● Панель администратора ({user.email})
        </div>
      </div>

      <h2 className="text-lg md:text-2xl font-black uppercase tracking-wide mb-4 md:mb-6">
        УПРАВЛЕНИЕ МАГАЗИНОМ
      </h2>

      <AdminNav activeTab={activeTab} onSelectTab={setActiveTab} />

      <main className="mt-6">
        <Suspense fallback={<div className="spinner" aria-label="Загрузка раздела" />}>
          {activeTab === 'catalog' && <ProductsTab />}
          {activeTab === 'brands' && <BrandsTab />}
          {activeTab === 'categories' && <CategoriesTab />}
          {activeTab === 'drops' && <DropsTab />}
          {activeTab === 'promocodes' && <PromocodesTab />}
          {activeTab === 'media' && <MediaTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'audit' && <AuditTab />}
          {activeTab === 'notifications' && <NotificationsAdminTab />}
        </Suspense>
      </main>
    </div>
  );
};
