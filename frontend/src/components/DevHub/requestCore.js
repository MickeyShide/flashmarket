export function buildRequest(endpoint, values) {
  let path = endpoint.path;
  for (const parameter of endpoint.pathParams || []) {
    const value = values.path?.[parameter.name];
    path = path.replace(`{${parameter.name}}`, encodeURIComponent(value ?? ''));
  }
  const query = new URLSearchParams();
  for (const parameter of endpoint.queryParams || []) {
    const value = values.query?.[parameter.name];
    if (value !== undefined && value !== null && value !== '') {
      query.set(parameter.name, String(value));
    }
  }
  if (query.size) path += `?${query.toString()}`;

  let headers = {};
  if (values.headers?.trim()) headers = JSON.parse(values.headers);
  headers = Object.fromEntries(
    Object.entries(headers).filter(([name]) => name.toLowerCase() !== 'authorization')
  );
  const options = { method: endpoint.method, headers };
  if (values.body?.trim()) {
    options.body = values.body;
    options.headers['Content-Type'] ||= 'application/json';
  }
  return { path, options };
}

export function shouldConfirm(endpoint) {
  return endpoint.method === 'DELETE'
    || (endpoint.access === 'admin' && !['GET', 'HEAD', 'OPTIONS'].includes(endpoint.method));
}
