import { api } from '../../services/api';
import { buildRequest } from './requestCore';

export { buildRequest, redactHeadersForDisplay, shouldConfirm } from './requestCore';

const SAFE_RESPONSE_HEADERS = new Set([
  'content-type',
  'content-length',
  'location',
  'retry-after',
  'x-request-id',
  'x-ratelimit-limit',
  'x-ratelimit-remaining',
]);

export async function executeRequest(endpoint, values) {
  const request = buildRequest(endpoint, values);
  const startedAt = performance.now();
  const response = await api(request.path, request.options);
  const body = await response.text();
  const elapsedMs = Math.max(0, Math.round(performance.now() - startedAt));
  const contentType = response.headers.get('content-type') || '';
  let data = body;
  if (body && contentType.includes('json')) {
    try {
      data = JSON.parse(body);
    } catch {
      data = body;
    }
  }
  const headers = {};
  response.headers.forEach((value, name) => {
    if (SAFE_RESPONSE_HEADERS.has(name.toLowerCase())) headers[name] = value;
  });
  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    elapsedMs,
    headers,
    contentType,
    rawBody: body,
    data,
  };
}
