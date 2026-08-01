import React from 'react';

const STACK = ['FastAPI', 'PostgreSQL', 'Redis', 'RabbitMQ', 'Nginx', 'React + Vite'];

export const DevHubFooter = ({ onBackToTop, onBackToStore }) => (
  <footer className="bg-black py-12 text-zinc-500">
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="flex flex-col justify-between gap-8 border-b border-zinc-800 pb-10 md:flex-row md:items-end">
        <div><div className="text-2xl font-black tracking-[-0.07em] text-white">FLASHMARKET</div><div className="mt-2 font-mono text-[9px] uppercase tracking-[0.2em]">Developer Hub · generated from deployed contracts</div></div>
        <div className="flex flex-wrap gap-2">{STACK.map((item) => <span key={item} className="border border-zinc-800 px-2.5 py-1.5 font-mono text-[9px] uppercase">{item}</span>)}</div>
      </div>
      <div className="mt-6 flex flex-wrap justify-between gap-4 font-mono text-[9px] uppercase tracking-wider"><span>Same-origin public API reference</span><div className="flex gap-5"><button onClick={onBackToStore} className="hover:text-[#BFF532]">Back to store</button><button onClick={onBackToTop} className="hover:text-[#BFF532]">Back to top ↑</button></div></div>
    </div>
  </footer>
);
