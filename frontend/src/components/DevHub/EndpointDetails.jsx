import React, { useState } from 'react';

const ACCESS_LABELS = { anonymous: 'Public', authenticated: 'Signed in', admin: 'Admin only' };

function ParameterTable({ title, parameters }) {
  if (!parameters.length) return null;
  return (
    <section className="mt-8">
      <h3 className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-500">{title}</h3>
      <div className="mt-3 border-t border-zinc-800">
        {parameters.map((parameter) => (
          <div key={`${parameter.location}:${parameter.name}`} className="grid gap-2 border-b border-zinc-800 py-4 sm:grid-cols-[150px_1fr]">
            <div className="font-mono text-xs text-[#BFF532]">{parameter.name}<div className="mt-1 text-[9px] uppercase text-zinc-600">{parameter.type}{parameter.required ? ' · required' : ''}</div></div>
            <p className="text-xs leading-5 text-zinc-400">{parameter.description || 'No additional description in the service contract.'}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export const EndpointDetails = ({ endpoint }) => {
  const [tab, setTab] = useState('contract');
  if (!endpoint) return <div className="flex h-full items-center justify-center p-8 text-sm text-zinc-500">Select an API operation.</div>;
  const responseEntries = Object.entries(endpoint.responses);
  return (
    <article className="h-[720px] overflow-y-auto bg-[#0D0D0E] p-6 sm:p-8">
      <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-widest">
        <span className="bg-white px-2 py-1 font-black text-black">{endpoint.method}</span>
        <span className={endpoint.access === 'admin' ? 'border border-rose-500/40 px-2 py-1 text-rose-400' : 'border border-zinc-700 px-2 py-1 text-zinc-400'}>{ACCESS_LABELS[endpoint.access]}</span>
        <span className="text-zinc-600">{endpoint.serviceId}</span>
      </div>
      <h2 className="mt-5 text-2xl font-black text-white sm:text-3xl">{endpoint.summary}</h2>
      <div className="mt-4 overflow-x-auto border-y border-zinc-800 py-4 font-mono text-sm text-[#BFF532]">{endpoint.path}</div>
      {endpoint.description ? <p className="mt-5 whitespace-pre-line text-sm leading-6 text-zinc-400">{endpoint.description}</p> : null}

      <div className="mt-8 flex gap-5 border-b border-zinc-800 font-mono text-[10px] uppercase tracking-wider">
        {['contract', 'responses'].map((item) => <button key={item} onClick={() => setTab(item)} className={`border-b-2 pb-3 ${tab === item ? 'border-[#BFF532] text-[#BFF532]' : 'border-transparent text-zinc-600'}`}>{item}</button>)}
      </div>

      {tab === 'contract' ? (
        <>
          <ParameterTable title="Path parameters" parameters={endpoint.pathParams} />
          <ParameterTable title="Query parameters" parameters={endpoint.queryParams} />
          <ParameterTable title="Header parameters" parameters={endpoint.headerParams} />
          {endpoint.requestBody ? (
            <section className="mt-8">
              <h3 className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-500">Request body · {endpoint.requestBody.contentType}</h3>
              {endpoint.requestBody.description ? <p className="mt-3 text-xs leading-5 text-zinc-400">{endpoint.requestBody.description}</p> : null}
              <pre className="mt-3 max-h-72 overflow-auto border border-zinc-800 bg-black p-4 font-mono text-[11px] leading-5 text-zinc-300">{JSON.stringify(endpoint.requestBody.schema, null, 2)}</pre>
            </section>
          ) : null}
        </>
      ) : (
        <section className="mt-6 space-y-3">
          {responseEntries.map(([status, response]) => (
            <div key={status} className="border border-zinc-800 bg-black p-4">
              <div className="font-mono text-xs font-bold text-[#BFF532]">HTTP {status}</div>
              <div className="mt-2 text-xs text-zinc-400">{response.description || 'Declared response'}</div>
              {response.content ? <pre className="mt-3 max-h-56 overflow-auto text-[10px] leading-5 text-zinc-500">{JSON.stringify(response.content, null, 2)}</pre> : null}
            </div>
          ))}
        </section>
      )}
    </article>
  );
};
