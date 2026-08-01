import React from 'react';

const STATUS_COLORS = {
  operational: 'text-accent-lime',
  degraded: 'text-accent-red',
  unknown: 'text-amber-400',
  checking: 'text-zinc-400',
};

function identityLabel(user, accessToken) {
  if (user?.role === 'ADMIN') return 'Администратор';
  if (user) return 'Покупатель';
  if (accessToken) return 'Авторизация...';
  return 'Гость';
}

export const DevHubHeader = ({ user, accessToken, systemStatus, onBackToStore }) => {
  const label = identityLabel(user, accessToken);
  const initials = user ? (user.full_name || user.email || 'U').slice(0, 2).toUpperCase() : 'GU';

  return (
    <header className="bg-[#111111] border-b border-[#27272A] sticky top-0 z-[100] w-full text-white">
      <div className="max-w-[1280px] mx-auto px-3.5 md:px-6 py-3 md:py-4 flex items-center justify-between gap-3">
        
        {/* Left: Back to store button */}
        <button
          onClick={onBackToStore}
          className="flex items-center gap-1.5 text-[10.5px] font-mono font-extrabold uppercase tracking-wider text-zinc-400 hover:text-accent-lime transition-colors cursor-pointer"
        >
          <svg className="w-4 h-4 stroke-current fill-none stroke-2 stroke-linecap-round stroke-linejoin-round" viewBox="0 0 24 24">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          <span className="hidden sm:inline">В МАГАЗИН</span>
        </button>

        {/* Center: Brand Title matching store header */}
        <div className="text-center flex-1 min-w-0 cursor-pointer" onClick={onBackToStore}>
          <h1 className="font-sans font-black text-sm md:text-xl tracking-[1px] md:tracking-[2.5px] uppercase select-none whitespace-nowrap leading-none text-white">
            FLASHMARKET <span className="text-accent-lime">DEV</span>
          </h1>
          <div className="font-mono text-[7.5px] md:text-[8.5px] tracking-[1px] md:tracking-[2px] uppercase text-zinc-400 mt-1 whitespace-nowrap">
            DEVELOPER HUB &amp; PUBLIC API
          </div>
        </div>

        {/* Right: Status Telemetry & User Access Badge */}
        <div className="flex items-center justify-end gap-3 font-mono">
          
          {/* Status Indicator */}
          <div className="hidden md:flex items-center gap-2 bg-[#1A1A1A] border border-[#333333] px-2.5 py-1 rounded text-[10px] uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-lime animate-pulse"></span>
            <span className={STATUS_COLORS[systemStatus.key] || 'text-accent-lime'}>
              {systemStatus.label}
            </span>
          </div>

          {/* User Role Access Pill */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:block text-right">
              <div className="text-[8px] uppercase tracking-widest text-zinc-500 font-extrabold">ДОСТУП</div>
              <div className="text-[10.5px] font-bold text-white">{label}</div>
            </div>
            <div className={`w-8 h-8 rounded flex items-center justify-center font-mono font-black text-[10.5px] border ${
              user?.role === 'ADMIN'
                ? 'bg-accent-lime/10 border-accent-lime text-accent-lime'
                : 'bg-[#1A1A1A] border-[#333333] text-zinc-300'
            }`}>
              {initials}
            </div>
          </div>

        </div>

      </div>
    </header>
  );
};
