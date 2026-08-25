const HTTP_METHODS = new Set(['get', 'post', 'put', 'patch', 'delete', 'options', 'head']);

function normalizeParameter(parameter) {
  return {
    ...parameter,
    default: parameter.schema?.default,
    required: Boolean(parameter.required),
  };
}

export function buildEndpointIndex(document) {
  const endpoints = [];
  for (const [path, pathItem] of Object.entries(document?.paths || {})) {
    const sharedParameters = pathItem.parameters || [];
    for (const [method, operation] of Object.entries(pathItem)) {
      if (!HTTP_METHODS.has(method) || !operation || typeof operation !== 'object') continue;
      const parameters = [...sharedParameters, ...(operation.parameters || [])].map(normalizeParameter);
      endpoints.push({
        id: operation.operationId || `${method}_${path}`,
        method: method.toUpperCase(),
        path,
        summary: operation.summary || '',
        serviceId: operation['x-flashmarket-service'] || 'unknown',
        access: operation['x-flashmarket-access'] || 'authenticated',
        pathParams: parameters.filter(parameter => parameter.in === 'path'),
        queryParams: parameters.filter(parameter => parameter.in === 'query'),
        headerParams: parameters.filter(parameter => parameter.in === 'header'),
        requestBody: operation.requestBody || null,
        responses: operation.responses || {},
      });
    }
  }
  return endpoints;
}

export function accessForUser(access, user, token) {
  if (access === 'anonymous') return { allowed: true, reason: null };
  if (!token || !user) return { allowed: false, reason: 'authentication_required' };
  if (access === 'admin' && user.role !== 'ADMIN') {
    return { allowed: false, reason: 'admin_required' };
  }
  return { allowed: true, reason: null };
}
