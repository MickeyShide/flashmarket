import React from 'react';

const STACK = ['FastAPI', 'PostgreSQL', 'Redis', 'RabbitMQ', 'Nginx', 'React + Vite'];

export const DevHubFooter = ({ onBackToTop, onBackToStore }) => (
  <footer className="bg-[#111111] border-t border-[#27272A] py-10 md:py-14 text-zinc-400 font-sans">
    <div className="max-w-[1280px] mx-auto px-3.5 md:px-6">
      
      {/* Top row */}
      <div className="flex flex-col justify-between gap-6 border-b border-[#27272A] pb-8 md:flex-row md:items-center">
        <div>
          <div className="font-sans font-black text-sm md:text-xl tracking-[1px] md:tracking-[2.5px] uppercase text-white">
            FLASHMARKET <span className="text-accent-lime">DEV</span>
          </div>
          <div className="mt-1 font-mono text-[7.5px] md:text-[8.5px] tracking-[1px] md:tracking-[2px] uppercase text-zinc-400">
            DEVELOPER HUB &amp; PUBLIC API CONTRACTS
          </div>
        </div>

        {/* Tech Stack Pills */}
        <div className="flex flex-wrap gap-1.5 font-mono text-[9.5px] uppercase font-bold">
          {STACK.map((item) => (
            <span
              key={item}
              className="border border-[#27272A] bg-[#18181B] px-3 py-1.5 rounded-sm text-zinc-300"
            >
              {item}
            </span>
          ))}
        </div>
      </div>

      {/* Bottom navigation links */}
      <div className="mt-6 flex flex-col sm:flex-row justify-between items-center gap-4 font-mono text-[9.5px] uppercase tracking-wider text-zinc-400 font-extrabold">
        <span>© 2026 FLASHMARKET. ВСЕ ПРАВА ZАЩИЩЕНЫ.</span>
        
        <div className="flex gap-6">
          <button
            onClick={onBackToStore}
            className="hover:text-accent-lime transition-colors cursor-pointer"
          >
            В МАГАЗИН ↗
          </button>
          <button
            onClick={onBackToTop}
            className="hover:text-accent-lime transition-colors cursor-pointer"
          >
            НАВЕРХ ↑
          </button>
        </div>
      </div>

    </div>
  </footer>
);
