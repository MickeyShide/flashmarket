import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { parseRoute, formatRouteUrl } from '../src/utils/router.js';

test('payment return route preserves the authoritative order id', () => {
  assert.deepEqual(parseRoute('/payment/return', '?order_id=order-123'), {
    view: 'payment-return',
    orderId: 'order-123',
  });
  assert.equal(
    formatRouteUrl({ view: 'payment-return', orderId: 'order-123' }),
    '/payment/return?order_id=order-123'
  );
});

test('order payment UI uses hosted checkout without client-side confirmation', async () => {
  const source = await readFile(
    new URL('../src/components/Order/OrderDetailView.jsx', import.meta.url),
    'utf8'
  );
  assert.match(source, /\/api\/v1\/payments\/orders\/\$\{orderId\}\/checkout/);
  assert.doesNotMatch(source, /\/api\/v1\/payments\/\$\{payment\.id\}\/confirm/);
  assert.doesNotMatch(source, /\/api\/v1\/orders\/\$\{orderId\}\/confirm/);
  assert.doesNotMatch(source, /amount:\s*payableAmountKopecks/);
});
