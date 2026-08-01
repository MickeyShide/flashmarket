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
    () => endpoint ? accessForUser(endpoint.access, user, accessToken) : { allowed: false, reason: '' },
    [endpoint, user, accessToken]
  );

  useEffect(() => {
    if (!endpoint) return;
    setPathValues(initialParameterValues(endpoint.pathParams));
    setQueryValues(initialParameterValues(endpoint.queryParams));
    setHeaders(JSON.stringify(Object.fromEntries(endpoint.headerParams.filter((item) => item.default !== '').map((item) => [item.name, item.default])), null, 2));
    setBody(endpoint.requestBody?.initialValue || '');
    setResponse(null);
    setError('');
    setConfirming(false);
  }, [endpoint]);

  if (!endpoint) return <aside className="h-full border-l border-zinc-800 bg-black" />;

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
      setError(requestError.message || 'The request could not be completed.');
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
  const truncatedResponse = renderedResponse.length > 100000 ? `${renderedResponse.slice(0, 100000)}\n… response truncated in viewer` : renderedResponse;

  return (
    <aside className="h-[720px] overflow-y-auto border-t border-zinc-800 bg-black font-mono lg:border-l lg:border-t-0">
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-zinc-800 bg-black/95 px-4 py-3 backdrop-blur">
        <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-white">Request console</span>
        <span className="max-w-44 truncate text-[9px] uppercase text-zinc-600">{window.location.host}</span>
      </div>
      <div className="space-y-5 p-4">
        {[['Path', endpoint.pathParams, pathValues, setPathValues], ['Query', endpoint.queryParams, queryValues, setQueryValues]].map(([title, parameters, values, setValues]) => parameters.length ? (
          <fieldset key={title} className="space-y-2">
            <legend className="mb-2 text-[9px] font-bold uppercase tracking-widest text-zinc-500">{title} parameters</legend>
            {parameters.map((parameter) => (
              <label key={parameter.name} className="block">
                <span className="mb-1 flex justify-between text-[9px] text-zinc-500"><span>{parameter.name}</span><span>{parameter.required ? 'required' : parameter.type}</span></span>
                <input value={values[parameter.name] ?? ''} onChange={(event) => setValues((current) => ({ ...current, [parameter.name]: event.target.value }))} className="w-full border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-white outline-none focus:border-[#BFF532]" />
              </label>
            ))}
          </fieldset>
        ) : null)}

        {endpoint.requestBody ? (
          <label className="block">
            <span className="mb-2 flex justify-between text-[9px] font-bold uppercase tracking-widest text-zinc-500"><span>Request body</span><button type="button" onClick={() => setBody(endpoint.requestBody.initialValue || '')} className="hover:text-white">Reset</button></span>
            <textarea rows={10} value={body} onChange={(event) => setBody(event.target.value)} spellCheck="false" className="w-full resize-y border border-zinc-800 bg-zinc-950 p-3 text-[11px] leading-5 text-emerald-300 outline-none focus:border-[#BFF532]" />
          </label>
        ) : null}

        <label className="block">
          <span className="mb-2 block text-[9px] font-bold uppercase tracking-widest text-zinc-500">Additional headers · Authorization managed by session</span>
          <textarea rows={4} value={headers} onChange={(event) => setHeaders(event.target.value)} spellCheck="false" className="w-full resize-y border border-zinc-800 bg-zinc-950 p-3 text-[11px] leading-5 text-amber-200 outline-none focus:border-[#BFF532]" />
        </label>

        {!access.allowed ? <div className="border border-amber-400/30 bg-amber-400/5 p-3 text-[10px] leading-5 text-amber-200">{access.reason}</div> : null}
        {confirming ? (
          <div role="alertdialog" aria-label="Confirm dangerous API request" className="border border-rose-500/40 bg-rose-500/5 p-4">
            <div className="text-[10px] font-bold uppercase text-rose-300">Confirm request</div>
            <div className="mt-2 break-all text-[10px] text-zinc-400">{endpoint.method} {endpoint.path}</div>
            <div className="mt-4 flex gap-2"><button onClick={() => run(true)} className="bg-rose-500 px-3 py-2 text-[9px] font-bold uppercase text-white">Run request</button><button onClick={() => setConfirming(false)} className="border border-zinc-700 px-3 py-2 text-[9px] uppercase text-zinc-300">Cancel</button></div>
          </div>
        ) : null}
        <button onClick={() => run(false)} disabled={!access.allowed || running} className="w-full bg-[#BFF532] px-4 py-3 text-[10px] font-black uppercase tracking-widest text-black disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500">
          {running ? 'Sending request…' : `Send ${endpoint.method}`}
        </button>
        {error ? <div className="border border-rose-500/30 bg-rose-500/5 p-3 text-[10px] leading-5 text-rose-300">{error}</div> : null}
        {response ? (
          <section className="border-t border-zinc-800 pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2 text-[9px] uppercase tracking-wider">
              <span className={response.ok ? 'font-bold text-emerald-400' : 'font-bold text-rose-400'}>HTTP {response.status} {response.statusText}</span>
              <span className="text-zinc-500">{response.elapsedMs} ms</span>
            </div>
            {Object.keys(response.headers).length ? <pre className="mt-3 overflow-auto border border-zinc-900 p-3 text-[9px] leading-4 text-zinc-500">{JSON.stringify(response.headers, null, 2)}</pre> : null}
            <pre className="mt-3 max-h-96 overflow-auto border border-zinc-800 bg-zinc-950 p-3 text-[10px] leading-5 text-zinc-300">{truncatedResponse || '(empty response body)'}</pre>
            <div className="mt-2 flex gap-3 text-[9px] uppercase text-zinc-500"><button onClick={() => navigator.clipboard.writeText(renderedResponse)} className="hover:text-white">Copy response</button><button onClick={download} className="hover:text-white">Download full body</button></div>
          </section>
        ) : null}
      </div>
    </aside>
  );
};
