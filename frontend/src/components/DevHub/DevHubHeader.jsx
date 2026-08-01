import React from 'react';

const STATUS_COLORS = {
  operational: 'text-[#BFF532]',
  degraded: 'text-rose-400',
  unknown: 'text-amber-300',
  checking: 'text-zinc-400',
};

function identityLabel(user, accessToken) {
  if (user?.role === 'ADMIN') return 'Administrator';
  if (user) return 'Customer';
  if (accessToken) return 'Loading account';
  return 'Guest';
}

export const DevHubHeader = ({ user, accessToken, systemStatus, onBackToStore }) => {
  const label = identityLabel(user, accessToken);
  const initials = user ? (user.full_name || user.email || 'U').slice(0, 2).toUpperCase() : 'GU';
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-800 bg-[#0B0B0C]/95 text-zinc-100 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <button onClick={onBackToStore} className="group flex items-center gap-3 rounded-sm text-left focus:outline-none focus:ring-2 focus:ring-[#BFF532]">
          <span className="text-xl font-black tracking-[-0.08em] text-white group-hover:text-[#BFF532]">FLASHMARKET</span>
          <span className="border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-[0.2em] text-zinc-300">DEV / 01</span>
        </button>

        <div className="hidden items-center gap-3 font-mono text-[10px] uppercase tracking-wider lg:flex">
          <span className="text-zinc-600">Gateway</span>
          <span className="text-[#BFF532]">→</span>
          <span className="text-zinc-300">Public API</span>
          <span className="text-[#BFF532]">→</span>
          <span className={STATUS_COLORS[systemStatus.key]}>{systemStatus.label}</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">Current access</div>
            <div className="text-xs font-bold text-white">{label}</div>
          </div>
          <div className={`flex h-9 w-9 items-center justify-center border font-mono text-[10px] font-bold ${user?.role === 'ADMIN' ? 'border-[#BFF532] text-[#BFF532]' : 'border-zinc-700 text-zinc-300'}`}>
            {initials}
          </div>
          <button onClick={onBackToStore} className="border-l border-zinc-800 pl-3 font-mono text-[10px] font-bold uppercase text-zinc-400 hover:text-[#BFF532]">
            Store ↗
          </button>
        </div>
      </div>
    </header>
  );
};
