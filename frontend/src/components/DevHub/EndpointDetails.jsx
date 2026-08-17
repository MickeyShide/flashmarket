import React, { useState } from 'react';

const ACCESS_LABELS = { anonymous: 'Публичный (Public)', authenticated: 'Авторизация (Signed In)', admin: 'Только Админ (Admin)' };

function ParameterTable({ title, parameters }) {
  if (!parameters.length) return null;
  return (
    <section className="mt-6">
      <h3 className="font-mono text-[10px] font-extrabold uppercase tracking-[1.5px] text-text-muted">
        {title}
      </h3>
      <div className="mt-2.5 border-t border-border-color">
        {parameters.map((parameter) => (
          <div key={`${parameter.location}:${parameter.name}`} className="grid gap-2 border-b border-border-color py-3 sm:grid-cols-[160px_1fr]">
            <div className="font-mono text-xs text-black font-bold">
              {parameter.name}
              <div className="mt-0.5 text-[9px] uppercase text-text-muted">
                {parameter.type}{parameter.required ? ' · обязательно' : ''}
              </div>
            </div>
            <p className="text-xs leading-relaxed text-zinc-700 font-sans">
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
      <div className="flex h-full items-center justify-center p-8 text-xs font-mono text-text-muted bg-white">
        Выберите операцию API из списка слева.
      </div>
    );
  }

  const responseEntries = Object.entries(endpoint.responses);

  return (
    <article className="h-[700px] overflow-y-auto bg-white p-5 sm:p-7 text-text-main font-sans">
      
      {/* Top Badges */}
      <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-wider font-extrabold">
        <span className="bg-black text-white px-2.5 py-1 rounded-sm">{endpoint.method}</span>
        <span className={`px-2.5 py-1 rounded-sm border ${
          endpoint.access === 'admin'
            ? 'border-red-200 text-red-700 bg-red-50'
            : endpoint.access === 'authenticated'
            ? 'border-blue-200 text-blue-700 bg-blue-50'
            : 'border-zinc-200 text-zinc-700 bg-zinc-100'
        }`}>
          {ACCESS_LABELS[endpoint.access]}
        </span>
        <span className="text-text-muted font-bold ml-auto">{endpoint.serviceId}</span>
      </div>

      {/* Operation Summary Header */}
      <h2 className="mt-4 font-sans font-black text-xl sm:text-2xl tracking-[0.5px] uppercase text-black">
        {endpoint.summary}
      </h2>

      {/* HTTP Path Box */}
      <div className="mt-3 overflow-x-auto border border-border-color bg-[#F9FAFB] p-3 rounded-sm font-mono text-xs sm:text-sm text-black font-black">
        {endpoint.path}
      </div>

      {endpoint.description && (
        <p className="mt-4 text-xs leading-relaxed text-zinc-700 whitespace-pre-line font-sans">
          {endpoint.description}
        </p>
      )}

      {/* Navigation Tabs */}
      <div className="mt-6 flex gap-6 border-b border-border-color font-mono text-[10.5px] font-extrabold uppercase tracking-wider">
        {['contract', 'responses'].map((item) => (
          <button
            key={item}
            onClick={() => setTab(item)}
            className={`border-b-2 pb-2.5 transition-colors cursor-pointer ${
              tab === item ? 'border-black text-black' : 'border-transparent text-text-muted hover:text-black'
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
              <h3 className="font-mono text-[10px] font-extrabold uppercase tracking-[1.5px] text-text-muted mb-2">
                Тело запроса (Request Body) · {endpoint.requestBody.contentType}
              </h3>
              {endpoint.requestBody.description && (
                <p className="text-xs text-zinc-700 mb-2 font-sans">{endpoint.requestBody.description}</p>
              )}
              <pre className="max-h-72 overflow-auto border border-border-color bg-[#F9FAFB] p-3.5 font-mono text-[11px] leading-relaxed text-zinc-900 rounded-sm">
                {JSON.stringify(endpoint.requestBody.schema, null, 2)}
              </pre>
            </section>
          )}
        </>
      ) : (
        /* Tab 2: Responses */
        <section className="mt-6 space-y-3 font-mono">
          {responseEntries.map(([status, response]) => (
            <div key={status} className="border border-border-color bg-[#F9FAFB] p-4 rounded-sm">
              <div className="text-xs font-black text-black">HTTP {status}</div>
              <div className="mt-1 text-xs text-zinc-700 font-sans">{response.description || 'Объявленный ответ'}</div>
              {response.content && (
                <pre className="mt-2.5 max-h-56 overflow-auto border border-border-color bg-white p-3 text-[10.5px] leading-relaxed text-zinc-800 rounded-sm">
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

