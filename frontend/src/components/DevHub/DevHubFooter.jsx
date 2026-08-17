import React from 'react';

const STACK = ['FastAPI', 'PostgreSQL', 'Redis', 'RabbitMQ', 'Nginx', 'React + Vite'];

export const DevHubFooter = ({ onBackToTop, onBackToStore, onOpenArchitecture }) => {
  const handleArchitectureClick = () => {
    if (onOpenArchitecture) {
      onOpenArchitecture();
    } else {
      window.open('/docs/architecture/', '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <footer className="bg-white border-t border-border-color py-10 md:py-14 text-text-muted font-sans">
      <div className="max-w-[1280px] mx-auto px-3.5 md:px-6">
        
        {/* Top row */}
        <div className="flex flex-col justify-between gap-6 border-b border-border-color pb-8 md:flex-row md:items-center">
          <div>
            <div className="font-sans font-black text-sm md:text-xl tracking-[1px] md:tracking-[2.5px] uppercase text-black">
              FLASHMARKET <span className="bg-[#BFF532] text-black px-1.5 py-0.5 rounded-sm text-xs font-mono">DEV</span>
            </div>
            <div className="mt-1 font-mono text-[7.5px] md:text-[8.5px] tracking-[1px] md:tracking-[2px] uppercase text-text-muted">
              DEVELOPER HUB &amp; PUBLIC API CONTRACTS
            </div>
          </div>

          {/* Tech Stack Pills */}
          <div className="flex flex-wrap gap-1.5 font-mono text-[9.5px] uppercase font-bold">
            {STACK.map((item) => (
              <span
                key={item}
                className="border border-border-color bg-[#F9FAFB] px-3 py-1.5 rounded-sm text-zinc-800"
              >
                {item}
              </span>
            ))}
          </div>
        </div>

        {/* Bottom navigation links */}
        <div className="mt-6 flex flex-col sm:flex-row justify-between items-center gap-4 font-mono text-[9.5px] uppercase tracking-wider text-text-muted font-extrabold">
          <span>© 2026 FLASHMARKET. ВСЕ ПРАВА ZАЩИЩЕНЫ.</span>
          
          <div className="flex items-center gap-6">
            <button
              onClick={onBackToStore}
              className="text-black hover:text-[#E53935] transition-colors cursor-pointer"
            >
              В МАГАЗИН ↗
            </button>
            <button
              onClick={handleArchitectureClick}
              className="text-black hover:text-[#2E7D32] font-black transition-colors cursor-pointer"
            >
              АРХИТЕКТУРА ↗
            </button>
            <button
              onClick={onBackToTop}
              className="text-black hover:text-text-muted transition-colors cursor-pointer"
            >
              НАВЕРХ ↑
            </button>
          </div>
        </div>

      </div>
    </footer>
  );
};

