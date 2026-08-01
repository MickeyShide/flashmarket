import assert from 'node:assert/strict';
import test from 'node:test';

import { accessForUser, buildEndpointIndex } from '../src/components/DevHub/openapi.js';
import { buildRequest, shouldConfirm } from '../src/components/DevHub/requestCore.js';

global.window = { location: { origin: 'https://flashmarket.example' } };

const document = {
  openapi: '3.1.0',
  paths: {
    '/api/v1/orders/{order_id}': {
      get: {
        operationId: 'get_order',
        summary: 'Get order',
        'x-flashmarket-service': 'orders',
        'x-flashmarket-access': 'authenticated',
        parameters: [
          { name: 'order_id', in: 'path', required: true, schema: { type: 'string', format: 'uuid' } },
          { name: 'include_items', in: 'query', schema: { type: 'boolean', default: false } },
        ],
        responses: { 200: { description: 'OK' } },
      },
    },
  },
  components: {},
};

test('buildEndpointIndex derives operations from OpenAPI', () => {
  const [endpoint] = buildEndpointIndex(document);
  assert.equal(endpoint.id, 'get_order');
  assert.equal(endpoint.serviceId, 'orders');
  assert.equal(endpoint.access, 'authenticated');
  assert.equal(endpoint.pathParams[0].name, 'order_id');
  assert.equal(endpoint.queryParams[0].default, false);
});

test('accessForUser enforces current session role', () => {
  assert.equal(accessForUser('anonymous', null, null).allowed, true);
  assert.equal(accessForUser('authenticated', null, null).allowed, false);
  assert.equal(accessForUser('admin', { role: 'CUSTOMER' }, 'token').allowed, false);
  assert.equal(accessForUser('admin', { role: 'ADMIN' }, 'token').allowed, true);
});

test('buildRequest serializes values and strips supplied authorization', () => {
  const [endpoint] = buildEndpointIndex(document);
  const request = buildRequest(endpoint, {
    path: { order_id: '5f2a' },
    query: { include_items: true },
    headers: JSON.stringify({ Authorization: 'Bearer must-not-leak', 'X-Request-ID': 'request-1' }),
    body: '',
  });
  assert.equal(request.path, '/api/v1/orders/5f2a?include_items=true');
  assert.equal(request.options.headers.Authorization, undefined);
  assert.equal(request.options.headers['X-Request-ID'], 'request-1');
});

test('dangerous and admin mutations require confirmation', () => {
  assert.equal(shouldConfirm({ method: 'DELETE', access: 'authenticated' }), true);
  assert.equal(shouldConfirm({ method: 'POST', access: 'admin' }), true);
  assert.equal(shouldConfirm({ method: 'GET', access: 'admin' }), false);
});
