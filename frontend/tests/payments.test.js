import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { parseRoute, formatRouteUrl } from '../src/utils/router.js';
import { paymentPollingDelay } from '../src/services/payment-polling.js';

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
  assert.match(source, /preparation_status/);
  assert.match(source, /waitForVisible/);
  assert.match(source, /current_attempt_status/);
});

test('payment polling uses bounded increasing delay with jitter', () => {
  const first = paymentPollingDelay(0, null, () => 0.5);
  const later = paymentPollingDelay(5, null, () => 0.5);
  const capped = paymentPollingDelay(100, null, () => 0.5);
  assert.equal(first, 500);
  assert.ok(later > first);
  assert.equal(capped, 8_000);
  assert.equal(paymentPollingDelay(0, 2, () => 0.5), 2_000);
});

test('return flow pauses polling in hidden tabs and supports cancellation', async () => {
  const source = await readFile(
    new URL('../src/components/Payment/PaymentReturnView.jsx', import.meta.url),
    'utf8'
  );
  assert.match(source, /waitForVisible/);
  assert.match(source, /AbortController/);
  assert.match(source, /paymentPollingDelay/);
  assert.doesNotMatch(source, /setTimeout\(\(\) => poll\(attempt \+ 1\), 2000\)/);
});
