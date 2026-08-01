import React, { useState } from 'react';

const ACCESS_LABELS = { anonymous: 'Публичный (Public)', authenticated: 'Авторизация (Signed In)', admin: 'Только Админ (Admin)' };

function ParameterTable({ title, parameters }) {
  if (!parameters.length) return null;
  return (
    <section className="mt-6">
      <h3 className="font-mono text-[10px] font-extrabold uppercase tracking-[1.5px] text-zinc-400">
        {title}
      </h3>
      <div className="mt-2.5 border-t border-[#27272A]">
        {parameters.map((parameter) => (
          <div key={`${parameter.location}:${parameter.name}`} className="grid gap-2 border-b border-[#27272A] py-3.5 sm:grid-cols-[160px_1fr]">
            <div className="font-mono text-xs text-accent-lime font-bold">
              {parameter.name}
              <div className="mt-0.5 text-[9px] uppercase text-zinc-500">
                {parameter.type}{parameter.required ? ' · обязательно' : ''}
              </div>
            </div>
            <p className="text-xs leading-relaxed text-zinc-300 font-sans">
              {parameter.description || 'Описание не указано в OpenAPI спецификации.'}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export const EndpointDetails = ({ endpoint }) => {
  const [tab, setTab] = useState('contract');

  if (!endpoint) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-xs font-mono text-zinc-500">
        Выберите операцию API из списка слева.
      </div>
    );
  }

  const responseEntries = Object.entries(endpoint.responses);

  return (
    <article className="h-[700px] overflow-y-auto bg-[#141414] p-5 sm:p-7 text-zinc-100 font-sans">
      
      {/* Top Badges */}
      <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-wider font-extrabold">
        <span className="bg-white text-black px-2.5 py-1 rounded-sm">{endpoint.method}</span>
        <span className={`px-2.5 py-1 rounded-sm border ${
          endpoint.access === 'admin'
            ? 'border-rose-500/40 text-rose-400 bg-rose-500/10'
            : endpoint.access === 'authenticated'
            ? 'border-cyan-500/40 text-cyan-400 bg-cyan-500/10'
            : 'border-zinc-700 text-zinc-300 bg-[#1A1A1A]'
        }`}>
          {ACCESS_LABELS[endpoint.access]}
        </span>
        <span className="text-zinc-500 ml-auto">{endpoint.serviceId}</span>
      </div>

      {/* Operation Summary Header */}
      <h2 className="mt-4 font-sans font-black text-xl sm:text-2xl tracking-[0.5px] uppercase text-white">
        {endpoint.summary}
      </h2>

      {/* HTTP Path Box */}
      <div className="mt-3 overflow-x-auto border border-[#27272A] bg-[#1A1A1A] p-3 rounded-sm font-mono text-xs sm:text-sm text-accent-lime font-bold">
        {endpoint.path}
      </div>

      {endpoint.description && (
        <p className="mt-4 text-xs leading-relaxed text-zinc-300 whitespace-pre-line font-sans">
          {endpoint.description}
        </p>
      )}

      {/* Navigation Tabs */}
      <div className="mt-6 flex gap-6 border-b border-[#27272A] font-mono text-[10.5px] font-extrabold uppercase tracking-wider">
        {['contract', 'responses'].map((item) => (
          <button
            key={item}
            onClick={() => setTab(item)}
            className={`border-b-2 pb-2.5 transition-colors cursor-pointer ${
              tab === item ? 'border-accent-lime text-accent-lime' : 'border-transparent text-zinc-400 hover:text-white'
            }`}
          >
            {item === 'contract' ? 'Параметры и Body' : 'HTTP Ответы (Responses)'}
          </button>
        ))}
      </div>

      {/* Tab 1: Contract Details */}
      {tab === 'contract' ? (
        <>
          <ParameterTable title="Path параметры" parameters={endpoint.pathParams} />
          <ParameterTable title="Query параметры" parameters={endpoint.queryParams} />
          <ParameterTable title="Header параметры" parameters={endpoint.headerParams} />

          {endpoint.requestBody && (
            <section className="mt-6">
              <h3 className="font-mono text-[10px] font-extrabold uppercase tracking-[1.5px] text-zinc-400 mb-2">
                Тело запроса (Request Body) · {endpoint.requestBody.contentType}
              </h3>
              {endpoint.requestBody.description && (
                <p className="text-xs text-zinc-300 mb-2 font-sans">{endpoint.requestBody.description}</p>
              )}
              <pre className="max-h-72 overflow-auto border border-[#27272A] bg-[#1A1A1A] p-3.5 font-mono text-[11px] leading-relaxed text-emerald-300 rounded-sm">
                {JSON.stringify(endpoint.requestBody.schema, null, 2)}
              </pre>
            </section>
          )}
        </>
      ) : (
        /* Tab 2: Responses */
        <section className="mt-6 space-y-3 font-mono">
          {responseEntries.map(([status, response]) => (
            <div key={status} className="border border-[#27272A] bg-[#1A1A1A] p-4 rounded-sm">
              <div className="text-xs font-black text-accent-lime">HTTP {status}</div>
              <div className="mt-1 text-xs text-zinc-300 font-sans">{response.description || 'Объявленный ответ'}</div>
              {response.content && (
                <pre className="mt-2.5 max-h-56 overflow-auto border border-[#27272A] bg-[#111111] p-3 text-[10.5px] leading-relaxed text-zinc-300 rounded-sm">
                  {JSON.stringify(response.content, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </section>
      )}

    </article>
  );
};
