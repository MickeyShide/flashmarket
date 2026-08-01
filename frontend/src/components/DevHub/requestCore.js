function parseHeaders(value) {
  if (!value.trim()) return {};
  const parsed = JSON.parse(value);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error('Headers must be a JSON object.');
  }
  const safe = {};
  for (const [name, headerValue] of Object.entries(parsed)) {
    if (name.toLowerCase() === 'authorization') continue;
    safe[name] = String(headerValue);
  }
  return safe;
}

function resolvedPath(endpoint, pathValues) {
  return endpoint.path.replace(/\{([^}]+)\}/g, (_, name) => {
    const value = pathValues[name];
    if (value === undefined || value === null || String(value).trim() === '') {
      throw new Error(`Path parameter “${name}” is required.`);
    }
    return encodeURIComponent(String(value));
  });
}

export function buildRequest(endpoint, values) {
  const url = new URL(resolvedPath(endpoint, values.path), window.location.origin);
  for (const parameter of endpoint.queryParams) {
    const value = values.query[parameter.name];
    if (parameter.required && String(value ?? '').trim() === '') {
      throw new Error(`Query parameter “${parameter.name}” is required.`);
    }
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      url.searchParams.set(parameter.name, String(value));
    }
  }

  const headers = { Accept: 'application/json', ...parseHeaders(values.headers) };
  const options = { method: endpoint.method, headers };
  if (endpoint.requestBody && values.body.trim()) {
    if (endpoint.requestBody.contentType === 'application/json') JSON.parse(values.body);
    headers['Content-Type'] = endpoint.requestBody.contentType;
    options.body = values.body;
  } else if (endpoint.requestBody?.required) {
    throw new Error('A request body is required.');
  }
  return { path: `${url.pathname}${url.search}`, options };
}

export function shouldConfirm(endpoint) {
  return endpoint.method === 'DELETE' || (endpoint.access === 'admin' && endpoint.method !== 'GET');
}

export function redactHeadersForDisplay(value) {
  try {
    return JSON.stringify(parseHeaders(value), null, 2);
  } catch {
    return value;
  }
}
