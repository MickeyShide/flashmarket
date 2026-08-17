import React from 'react';

const STATUS_COLORS = {
  operational: 'text-[#2E7D32]',
  degraded: 'text-accent-red',
  unknown: 'text-amber-600',
  checking: 'text-zinc-500',
};

function identityLabel(user, accessToken) {
  if (user?.role === 'ADMIN') return 'Администратор';
  if (user) return 'Покупатель';
  if (accessToken) return 'Авторизация...';
  return 'Гость';
}

export const DevHubHeader = ({ user, accessToken, systemStatus, onBackToStore, onArchitectureClick }) => {
  const label = identityLabel(user, accessToken);
  const initials = user ? (user.full_name || user.email || 'U').slice(0, 2).toUpperCase() : 'GU';

  const handleOpenArchitecture = () => {
    if (onArchitectureClick) {
      onArchitectureClick();
    } else {
      window.open('/docs/architecture/', '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <header className="bg-white border-b border-border-color sticky top-0 z-[100] w-full text-text-main">
      <div className="max-w-[1280px] mx-auto px-3.5 md:px-6 py-3 md:py-4 flex items-center justify-between gap-3">
        
        {/* Left: Back to store & Architecture Link */}
        <div className="flex items-center gap-2 md:gap-3">
          <button
            onClick={onBackToStore}
            className="flex items-center gap-1.5 text-[10.5px] font-mono font-extrabold uppercase tracking-wider text-text-muted hover:text-black transition-colors cursor-pointer"
            title="Вернуться в витрину магазина"
          >
            <svg className="w-4 h-4 stroke-current fill-none stroke-2 stroke-linecap-round stroke-linejoin-round" viewBox="0 0 24 24">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span className="hidden sm:inline">В МАГАЗИН</span>
          </button>

          <button
            onClick={handleOpenArchitecture}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider bg-black text-[#BFF532] hover:bg-zinc-800 rounded transition-colors cursor-pointer border border-black"
            title="Открыть интерактивную страницу архитектуры системы"
          >
            <span>АРХИТЕКТУРА</span>
            <span className="text-white">↗</span>
          </button>
        </div>

        {/* Center: Brand Title matching store header */}
        <div className="text-center flex-1 min-w-0 cursor-pointer" onClick={onBackToStore}>
          <h1 className="font-sans font-black text-sm md:text-xl tracking-[1px] md:tracking-[2.5px] uppercase select-none whitespace-nowrap leading-none text-black">
            FLASHMARKET <span className="text-[#888888] font-normal">/</span> <span className="bg-[#BFF532] text-black px-1.5 py-0.5 rounded-sm">DEV</span>
          </h1>
          <div className="font-mono text-[7.5px] md:text-[8.5px] tracking-[1px] md:tracking-[2px] uppercase text-text-muted mt-1 whitespace-nowrap">
            DEVELOPER HUB &amp; PUBLIC API
          </div>
        </div>

        {/* Right: Status Telemetry & User Access Badge */}
        <div className="flex items-center justify-end gap-2 md:gap-3 font-mono">
          
          {/* Status Indicator */}
          <div className="hidden md:flex items-center gap-2 bg-[#F9FAFB] border border-border-color px-2.5 py-1 rounded text-[10px] uppercase tracking-wider font-extrabold">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2E7D32] animate-pulse"></span>
            <span className={STATUS_COLORS[systemStatus.key] || 'text-[#2E7D32]'}>
              {systemStatus.label}
            </span>
          </div>

          {/* User Role Access Pill */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:block text-right">
              <div className="text-[8px] uppercase tracking-widest text-text-muted font-extrabold">ДОСТУП</div>
              <div className="text-[10.5px] font-bold text-black">{label}</div>
            </div>
            <div className={`w-8 h-8 rounded flex items-center justify-center font-mono font-black text-[10.5px] border ${
              user?.role === 'ADMIN'
                ? 'bg-red-50 border-accent-red text-accent-red'
                : 'bg-[#F9FAFB] border-border-color text-black'
            }`}>
              {initials}
            </div>
          </div>

        </div>

      </div>
    </header>
  );
};

