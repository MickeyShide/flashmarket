import React, { useEffect, useMemo, useState } from 'react';
import { accessForUser } from './openapi';
import { executeRequest, shouldConfirm } from './request';

function initialParameterValues(parameters) {
  return Object.fromEntries(parameters.map((parameter) => [parameter.name, parameter.default ?? '']));
}

function responseText(response) {
  if (!response) return '';
  return typeof response.data === 'string' ? response.data : JSON.stringify(response.data, null, 2);
}

export const RequestPlayground = ({ endpoint, user, accessToken }) => {
  const [pathValues, setPathValues] = useState({});
  const [queryValues, setQueryValues] = useState({});
  const [headers, setHeaders] = useState('{}');
  const [body, setBody] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const access = useMemo(
    () => (endpoint ? accessForUser(endpoint.access, user, accessToken) : { allowed: false, reason: '' }),
    [endpoint, user, accessToken]
  );

  useEffect(() => {
    if (!endpoint) return;
    setPathValues(initialParameterValues(endpoint.pathParams));
    setQueryValues(initialParameterValues(endpoint.queryParams));
    setHeaders(
      JSON.stringify(
        Object.fromEntries(
          endpoint.headerParams.filter((item) => item.default !== '').map((item) => [item.name, item.default])
        ),
        null,
        2
      )
    );
    setBody(endpoint.requestBody?.initialValue || '');
    setResponse(null);
    setError('');
    setConfirming(false);
  }, [endpoint]);

  if (!endpoint) return <aside className="h-full border-l border-border-color bg-[#FAFAFA]" />;

  const run = async (confirmed = false) => {
    if (shouldConfirm(endpoint) && !confirmed) {
      setConfirming(true);
      return;
    }
    setConfirming(false);
    setRunning(true);
    setError('');
    setResponse(null);
    try {
      const result = await executeRequest(endpoint, { path: pathValues, query: queryValues, headers, body });
      setResponse(result);
    } catch (requestError) {
      setError(requestError.message || 'Ошибка выполнения запроса.');
    } finally {
      setRunning(false);
    }
  };

  const download = () => {
    const blob = new Blob([response.rawBody], { type: response.contentType || 'text/plain' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `flashmarket-${endpoint.operationId || 'response'}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const renderedResponse = responseText(response);
  const truncatedResponse =
    renderedResponse.length > 100000
      ? `${renderedResponse.slice(0, 100000)}\n… ответ сокращен`
      : renderedResponse;

  return (
    <aside className="h-[700px] overflow-y-auto border-t border-border-color bg-[#FAFAFA] font-mono lg:border-l lg:border-t-0 text-text-main">
      
      {/* Playground Console Header */}
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border-color bg-white px-4 py-3">
        <span className="text-[10.5px] font-black uppercase tracking-wider text-black">
          КОНСОЛЬ ЗАПРОСОВ
        </span>
        <span className="max-w-44 truncate text-[9.5px] uppercase text-text-muted font-bold">
          {window.location.host}
        </span>
      </div>

      <div className="space-y-4 p-4">
        
        {/* Parameter Fields */}
        {[
          ['Path', endpoint.pathParams, pathValues, setPathValues],
          ['Query', endpoint.queryParams, queryValues, setQueryValues],
        ].map(([title, parameters, values, setValues]) =>
          parameters.length ? (
            <fieldset key={title} className="space-y-2">
              <legend className="mb-1 text-[9.5px] font-extrabold uppercase tracking-wider text-text-muted">
                {title} Параметры
              </legend>
              {parameters.map((parameter) => (
                <label key={parameter.name} className="block">
                  <span className="mb-1 flex justify-between text-[9px] text-text-muted">
                    <span>{parameter.name}</span>
                    <span>{parameter.required ? 'обязательно' : parameter.type}</span>
                  </span>
                  <input
                    value={values[parameter.name] ?? ''}
                    onChange={(event) =>
                      setValues((current) => ({ ...current, [parameter.name]: event.target.value }))
                    }
                    className="w-full border border-border-color bg-white px-3 py-2 text-xs text-black outline-none focus:border-black rounded-sm"
                  />
                </label>
              ))}
            </fieldset>
          ) : null
        )}

        {/* Request Body */}
        {endpoint.requestBody && (
          <label className="block">
            <span className="mb-1.5 flex justify-between text-[9.5px] font-extrabold uppercase tracking-wider text-text-muted">
              <span>Тело запроса (JSON)</span>
              <button
                type="button"
                onClick={() => setBody(endpoint.requestBody.initialValue || '')}
                className="hover:text-black underline cursor-pointer font-bold"
              >
                Сбросить
              </button>
            </span>
            <textarea
              rows={8}
              value={body}
              onChange={(event) => setBody(event.target.value)}
              spellCheck="false"
              className="w-full resize-y border border-border-color bg-white p-3 text-[11px] leading-relaxed text-zinc-900 outline-none focus:border-black rounded-sm"
            />
          </label>
        )}

        {/* Additional Headers */}
        <label className="block">
          <span className="mb-1.5 block text-[9.5px] font-extrabold uppercase tracking-wider text-text-muted">
            Заголовки (Headers)
          </span>
          <textarea
            rows={3}
            value={headers}
            onChange={(event) => setHeaders(event.target.value)}
            spellCheck="false"
            className="w-full resize-y border border-border-color bg-white p-2.5 text-[11px] leading-relaxed text-zinc-900 outline-none focus:border-black rounded-sm"
          />
        </label>

        {/* Role Access Restriction Warning */}
        {!access.allowed && (
          <div className="border border-amber-300 bg-amber-50 p-3 text-[10.5px] leading-relaxed text-amber-900 rounded-sm font-sans">
            {access.reason}
          </div>
        )}

        {/* Confirmation modal for dangerous operations */}
        {confirming && (
          <div role="alertdialog" className="border border-red-300 bg-red-50 p-4 rounded-sm">
            <div className="text-[10.5px] font-black uppercase text-red-800">Подтвердите выполнение</div>
            <div className="mt-1 break-all text-[10px] text-zinc-700 font-mono">
              {endpoint.method} {endpoint.path}
            </div>
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => run(true)}
                className="bg-red-600 hover:bg-red-700 px-3 py-1.5 text-[9.5px] font-black uppercase text-white rounded-sm cursor-pointer"
              >
                Выполнить
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="border border-border-color bg-white hover:bg-zinc-100 px-3 py-1.5 text-[9.5px] uppercase text-black rounded-sm cursor-pointer"
              >
                Отмена
              </button>
            </div>
          </div>
        )}

        {/* Execute Button matching FlashMarket store buttons */}
        <button
          onClick={() => run(false)}
          disabled={!access.allowed || running}
          className="w-full bg-[#BFF532] text-black px-4 py-3 text-[10.5px] font-black tracking-[1.5px] uppercase rounded-sm cursor-pointer hover:bg-black hover:text-[#BFF532] disabled:cursor-not-allowed disabled:bg-zinc-200 disabled:text-zinc-400 transition-all shadow-xs border border-black"
        >
          {running ? 'ОТПРАВКА ЗАПРОСА...' : `ОТПРАВИТЬ ${endpoint.method}`}
        </button>

        {error && (
          <div className="border border-red-300 bg-red-50 p-3 text-[10.5px] leading-relaxed text-red-800 rounded-sm">
            {error}
          </div>
        )}

        {/* Response output viewer */}
        {response && (
          <section className="border-t border-border-color pt-4">
            <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] uppercase font-bold">
              <span className={response.ok ? 'text-[#2E7D32]' : 'text-red-700'}>
                HTTP {response.status} {response.statusText}
              </span>
              <span className="text-text-muted">{response.elapsedMs} ms</span>
            </div>

            {Object.keys(response.headers).length > 0 && (
              <pre className="mt-2.5 overflow-auto border border-border-color bg-white p-2.5 text-[9.5px] leading-relaxed text-zinc-700 rounded-sm">
                {JSON.stringify(response.headers, null, 2)}
              </pre>
            )}

            <pre className="mt-2.5 max-h-80 overflow-auto border border-border-color bg-white p-3 text-[10.5px] leading-relaxed text-zinc-900 rounded-sm">
              {truncatedResponse || '(пустое тело ответа)'}
            </pre>

            <div className="mt-2.5 flex gap-2 text-[9.5px] uppercase font-bold">
              <button
                onClick={() => navigator.clipboard.writeText(renderedResponse)}
                className="bg-white border border-border-color px-2.5 py-1 rounded-sm text-black hover:bg-black hover:text-white transition-colors cursor-pointer"
              >
                Скопировать ответ
              </button>
              <button
                onClick={download}
                className="bg-white border border-border-color px-2.5 py-1 rounded-sm text-black hover:bg-black hover:text-white transition-colors cursor-pointer"
              >
                Скачать JSON
              </button>
            </div>
          </section>
        )}

      </div>
    </aside>
  );
};

