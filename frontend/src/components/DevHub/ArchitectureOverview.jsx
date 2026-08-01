import React from 'react';

export const ArchitectureOverview = ({ services }) => (
  <section id="architecture-overview" className="scroll-mt-16 border-b border-zinc-800 bg-[#0E0E0F] py-16">
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="mb-10"><div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-[#BFF532]">Request topology</div><h2 className="mt-2 text-3xl font-black uppercase text-white sm:text-4xl">Public outside. Isolated inside.</h2></div>
      <div className="grid gap-px border border-zinc-800 bg-zinc-800 lg:grid-cols-[1fr_80px_1fr_80px_2fr]">
        <div className="bg-zinc-950 p-6"><span className="font-mono text-[9px] uppercase text-zinc-600">Client</span><h3 className="mt-6 text-xl font-black uppercase text-white">Browser</h3><p className="mt-2 text-xs text-zinc-500">Same-origin HTTPS requests</p></div>
        <div className="hidden items-center justify-center bg-zinc-950 font-mono text-[#BFF532] lg:flex">→</div>
        <div className="bg-zinc-950 p-6"><span className="font-mono text-[9px] uppercase text-zinc-600">Edge</span><h3 className="mt-6 text-xl font-black uppercase text-white">Nginx Gateway</h3><p className="mt-2 text-xs text-zinc-500">Routing, rate limits and forwarded identity</p></div>
        <div className="hidden items-center justify-center bg-zinc-950 font-mono text-[#BFF532] lg:flex">→</div>
        <div className="bg-zinc-950 p-6"><span className="font-mono text-[9px] uppercase text-zinc-600">Docker network</span><div className="mt-5 flex flex-wrap gap-2">{services.map((service) => <span key={service.id} className="border border-zinc-800 px-2.5 py-1.5 font-mono text-[9px] uppercase text-zinc-300">{service.id}</span>)}</div></div>
      </div>
      <div className="mt-px grid gap-px bg-zinc-800 md:grid-cols-2">
        <div className="bg-black p-5"><div className="font-mono text-[10px] font-bold uppercase text-emerald-400">Public route</div><div className="mt-2 font-mono text-sm text-white">/api/v1/* · /auth/* · /users/*</div></div>
        <div className="bg-black p-5"><div className="font-mono text-[10px] font-bold uppercase text-rose-400">Not routed externally</div><div className="mt-2 font-mono text-sm text-white">/internal/*</div></div>
      </div>
    </div>
  </section>
);
