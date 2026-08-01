import React, { useMemo, useState } from 'react';

export const DevHubHero = ({ metadata, endpoints, onExploreClick, onArchitectureClick }) => {
  const [copied, setCopied] = useState(false);
  const sample = useMemo(
    () => endpoints.find((endpoint) => endpoint.access === 'anonymous' && endpoint.method === 'GET') || endpoints[0],
    [endpoints]
  );
  const sampleCommand = sample
    ? `curl --request ${sample.method} "${window.location.origin}${sample.path}" \\\n  --header "Accept: application/json"`
    : '';
  const copy = async () => {
    await navigator.clipboard.writeText(sampleCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section className="relative overflow-hidden border-b border-zinc-800 bg-[#0B0B0C] py-16 sm:py-24">
      <div className="pointer-events-none absolute inset-0 opacity-20 [background-image:linear-gradient(#27272a_1px,transparent_1px),linear-gradient(90deg,#27272a_1px,transparent_1px)] [background-size:48px_48px]" />
      <div className="relative mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-12 lg:px-8">
        <div className="lg:col-span-7">
          <div className="mb-5 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-[0.18em]">
            <span className="bg-[#BFF532] px-2.5 py-1 font-bold text-black">API {metadata.version}</span>
            <span className="border border-zinc-700 bg-zinc-900 px-2.5 py-1 text-zinc-300">OpenAPI {metadata.openapi}</span>
            <span className="border border-zinc-700 bg-zinc-900 px-2.5 py-1 text-zinc-300">Same origin</span>
          </div>
          <h1 className="max-w-4xl text-5xl font-black uppercase leading-[0.92] tracking-[-0.065em] text-white sm:text-7xl lg:text-[88px]">
            The API behind <span className="text-[#BFF532]">the drop.</span>
          </h1>
          <p className="mt-7 max-w-2xl text-base leading-7 text-zinc-300 sm:text-lg">
            Inspect the live contracts that connect identity, catalog, stock, checkout and fulfillment across FlashMarket.
          </p>
          <div className="mt-10 grid max-w-2xl grid-cols-3 border-y border-zinc-800 py-5 font-mono">
            <div><strong className="block text-2xl text-white">{metadata.serviceCount}</strong><span className="text-[9px] uppercase tracking-widest text-zinc-500">Services</span></div>
            <div><strong className="block text-2xl text-[#BFF532]">{metadata.operationCount}</strong><span className="text-[9px] uppercase tracking-widest text-zinc-500">Operations</span></div>
            <div><strong className="block text-2xl text-white">{Object.keys(metadata).length ? 'REST' : '—'}</strong><span className="text-[9px] uppercase tracking-widest text-zinc-500">Interface</span></div>
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <button onClick={onExploreClick} className="bg-[#BFF532] px-6 py-3.5 font-mono text-xs font-bold uppercase tracking-wider text-black hover:bg-white">Explore API ↓</button>
            <button onClick={onArchitectureClick} className="border border-zinc-700 bg-zinc-950 px-6 py-3.5 font-mono text-xs font-bold uppercase tracking-wider text-zinc-200 hover:border-zinc-500">Architecture →</button>
          </div>
        </div>

        <div className="self-end lg:col-span-5">
          <div className="border border-zinc-700 bg-black shadow-[16px_16px_0_0_#BFF532]">
            <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              <span>Current origin / {sample?.serviceId || 'api'}</span>
              <button onClick={copy} className="text-zinc-300 hover:text-[#BFF532]">{copied ? 'Copied' : 'Copy'}</button>
            </div>
            <pre className="min-h-48 overflow-x-auto whitespace-pre-wrap p-5 font-mono text-xs leading-6 text-zinc-300"><span className="text-[#BFF532]">$ </span>{sampleCommand}</pre>
            <div className="grid grid-cols-[auto_1fr] gap-px border-t border-zinc-800 bg-zinc-800 font-mono text-[10px]">
              <span className="bg-zinc-950 px-4 py-3 font-bold text-emerald-400">{sample?.method || 'GET'}</span>
              <span className="truncate bg-zinc-950 px-4 py-3 text-zinc-400">{sample?.path || '/'}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
