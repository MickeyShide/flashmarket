import React from 'react';

export const AdminNav = ({ activeTab, onSelectTab }) => {
  const tabs = [
    { id: 'catalog', label: 'Товары' },
    { id: 'brands', label: 'Бренды' },
    { id: 'categories', label: 'Категории' },
    { id: 'drops', label: 'Дропы' },
    { id: 'promocodes', label: 'Промокоды' },
    { id: 'media', label: 'Медиа' },
    { id: 'users', label: 'Пользователи' },
    { id: 'audit', label: 'Аудит' },
    { id: 'notifications', label: 'Уведомления' },
  ];

  return (
    <div className="flex border-b border-border-color mb-6 gap-2 md:gap-4 overflow-x-auto no-scrollbar bg-white p-2 rounded-lg border">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`px-3 py-2 text-xs font-black tracking-wider uppercase cursor-pointer whitespace-nowrap rounded transition-colors ${
            activeTab === tab.id
              ? 'bg-black text-white'
              : 'text-gray-600 hover:text-black hover:bg-gray-100'
          }`}
          onClick={() => onSelectTab(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};
