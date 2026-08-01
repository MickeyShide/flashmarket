const HTTP_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace'];

export function resolveReference(document, value) {
  if (!value || typeof value !== 'object' || !value.$ref) return value;
  if (!value.$ref.startsWith('#/')) return value;
  return value.$ref
    .slice(2)
    .split('/')
    .reduce((current, segment) => current?.[segment.replaceAll('~1', '/').replaceAll('~0', '~')], document);
}

function schemaType(schema, document) {
  const resolved = resolveReference(document, schema) || {};
  if (resolved.type) return Array.isArray(resolved.type) ? resolved.type.join(' | ') : resolved.type;
  if (resolved.anyOf) return resolved.anyOf.map((item) => schemaType(item, document)).join(' | ');
  if (resolved.oneOf) return resolved.oneOf.map((item) => schemaType(item, document)).join(' | ');
  return 'value';
}

function schemaTemplate(schema, document, depth = 0) {
  if (depth > 5) return null;
  const resolved = resolveReference(document, schema) || {};
  if (resolved.example !== undefined) return resolved.example;
  if (resolved.default !== undefined) return resolved.default;
  if (Array.isArray(resolved.enum) && resolved.enum.length > 0) return resolved.enum[0];
  if (resolved.anyOf) {
    const candidate = resolved.anyOf.find((item) => schemaType(item, document) !== 'null');
    return schemaTemplate(candidate || resolved.anyOf[0], document, depth + 1);
  }
  if (resolved.oneOf) return schemaTemplate(resolved.oneOf[0], document, depth + 1);
  if (resolved.type === 'object' || resolved.properties) {
    return Object.fromEntries(
      Object.entries(resolved.properties || {}).map(([name, property]) => [
        name,
        schemaTemplate(property, document, depth + 1),
      ])
    );
  }
  if (resolved.type === 'array') return [];
  if (resolved.type === 'boolean') return false;
  if (resolved.type === 'integer' || resolved.type === 'number') return 0;
  if (resolved.type === 'string') return '';
  return null;
}

function normalizeParameter(parameter, document) {
  const resolved = resolveReference(document, parameter) || parameter;
  const schema = resolveReference(document, resolved.schema) || resolved.schema || {};
  return {
    name: resolved.name,
    location: resolved.in,
    required: Boolean(resolved.required),
    description: resolved.description || '',
    type: schemaType(schema, document),
    format: schema.format || '',
    default: schema.example ?? schema.default ?? '',
    schema,
  };
}

function requestBodyFor(operation, document) {
  const requestBody = resolveReference(document, operation.requestBody);
  if (!requestBody) return null;
  const content = requestBody.content || {};
  const contentType = content['application/json'] ? 'application/json' : Object.keys(content)[0];
  if (!contentType) return null;
  const media = content[contentType] || {};
  const schema = resolveReference(document, media.schema) || media.schema || {};
  const example = media.example ?? schemaTemplate(schema, document);
  return {
    required: Boolean(requestBody.required),
    description: requestBody.description || '',
    contentType,
    schema,
    initialValue: example === undefined ? '' : JSON.stringify(example, null, 2),
  };
}

export function buildEndpointIndex(document) {
  const endpoints = [];
  for (const [path, pathItem] of Object.entries(document.paths || {})) {
    const sharedParameters = pathItem.parameters || [];
    for (const method of HTTP_METHODS) {
      const operation = pathItem[method];
      if (!operation || typeof operation !== 'object') continue;
      const parameters = [...sharedParameters, ...(operation.parameters || [])].map((parameter) =>
        normalizeParameter(parameter, document)
      );
      const serviceId = operation['x-flashmarket-service'];
      const access = operation['x-flashmarket-access'];
      endpoints.push({
        id: operation.operationId || `${method}:${path}`,
        operationId: operation.operationId || '',
        serviceId,
        method: method.toUpperCase(),
        path,
        summary: operation.summary || `${method.toUpperCase()} ${path}`,
        description: operation.description || '',
        access,
        deprecated: Boolean(operation.deprecated),
        tags: operation.tags || [],
        pathParams: parameters.filter((parameter) => parameter.location === 'path'),
        queryParams: parameters.filter((parameter) => parameter.location === 'query'),
        headerParams: parameters.filter((parameter) => parameter.location === 'header'),
        requestBody: requestBodyFor(operation, document),
        responses: operation.responses || {},
        security: operation.security || [],
        operation,
      });
    }
  }
  return endpoints.sort((left, right) =>
    left.serviceId.localeCompare(right.serviceId) ||
    left.path.localeCompare(right.path) ||
    left.method.localeCompare(right.method)
  );
}

export function accessForUser(access, user, accessToken) {
  if (access === 'anonymous') return { allowed: true, reason: '' };
  if (!accessToken || !user) {
    return { allowed: false, reason: accessToken ? 'Loading your account…' : 'Sign in to run this operation.' };
  }
  if (access === 'admin' && user.role !== 'ADMIN') {
    return { allowed: false, reason: 'Administrator role required.' };
  }
  return { allowed: true, reason: '' };
}

export async function loadDeveloperHubData(signal) {
  const requestOptions = { signal, cache: 'no-store', headers: { Accept: 'application/json' } };
  const [openapiResponse, servicesResponse] = await Promise.all([
    fetch('/dev/openapi.json', requestOptions),
    fetch('/dev/services.json', requestOptions),
  ]);
  if (!openapiResponse.ok || !servicesResponse.ok) {
    throw new Error('Generated API contract is unavailable.');
  }
  const [openapi, metadata] = await Promise.all([openapiResponse.json(), servicesResponse.json()]);
  if (!String(openapi.openapi || '').startsWith('3.1.') || !openapi.paths || !Array.isArray(metadata.services)) {
    throw new Error('Generated API contract is invalid.');
  }
  return { openapi, metadata, endpoints: buildEndpointIndex(openapi) };
}

async function probeService(service, parentSignal) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 3500);
  const abortFromParent = () => controller.abort();
  parentSignal?.addEventListener('abort', abortFromParent, { once: true });
  try {
    const response = await fetch(service.statusUrl, {
      signal: controller.signal,
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
    return [service.id, response.ok ? 'operational' : 'unavailable'];
  } catch (error) {
    return [service.id, error?.name === 'AbortError' ? 'unknown' : 'unavailable'];
  } finally {
    window.clearTimeout(timeout);
    parentSignal?.removeEventListener('abort', abortFromParent);
  }
}

export async function loadServiceStatuses(services, signal) {
  const entries = await Promise.all(services.map((service) => probeService(service, signal)));
  return Object.fromEntries(entries);
}

export function describeSystemStatus(statuses, serviceCount) {
  const values = Object.values(statuses);
  if (values.length < serviceCount) return { key: 'checking', label: 'Checking services' };
  if (values.some((status) => status === 'unavailable')) return { key: 'degraded', label: 'Service degradation' };
  if (values.some((status) => status === 'unknown')) return { key: 'unknown', label: 'Status incomplete' };
  return { key: 'operational', label: 'All systems operational' };
}
