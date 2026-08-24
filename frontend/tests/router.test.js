import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseRoute, formatRouteUrl } from '../src/utils/router.js';

test('parseRoute maps URLs to correct views and parameters', () => {
  assert.deepEqual(parseRoute('/product/hoodie-black'), {
    view: 'product',
    productSlug: 'hoodie-black',
  });

  assert.deepEqual(parseRoute('/products/hoodie-black'), {
    view: 'product',
    productSlug: 'hoodie-black',
  });

  assert.deepEqual(parseRoute('/drops/summer-drop'), {
    view: 'drop-detail',
    dropIdentifier: 'summer-drop',
  });

  assert.deepEqual(parseRoute('/drops'), {
    view: 'drops',
  });

  assert.deepEqual(parseRoute('/cart'), {
    view: 'cart',
  });

  assert.deepEqual(parseRoute('/checkout'), {
    view: 'checkout',
  });

  assert.deepEqual(parseRoute('/payment/return', '?order_id=order-123'), {
    view: 'payment-return',
    orderId: 'order-123',
  });

  assert.deepEqual(parseRoute('/profile/wishlist'), {
    view: 'auth',
    profileTab: 'wishlist',
  });

  assert.deepEqual(parseRoute('/profile/orders'), {
    view: 'auth',
    profileTab: 'orders',
  });

  assert.deepEqual(parseRoute('/orders/order-uuid-123'), {
    view: 'order-detail',
    orderId: 'order-uuid-123',
  });

  assert.deepEqual(parseRoute('/architecture'), {
    view: 'architecture',
  });

  assert.deepEqual(parseRoute('/docs/architecture'), {
    view: 'architecture',
  });

  assert.deepEqual(parseRoute('/docs/architecture/'), {
    view: 'architecture',
  });

  assert.deepEqual(parseRoute('/dev'), {
    view: 'dev',
  });

  assert.deepEqual(parseRoute('/admin'), {
    view: 'admin',
  });

  assert.deepEqual(parseRoute('/'), {
    view: 'catalog',
  });
});

test('formatRouteUrl generates clean canonical URLs', () => {
  assert.equal(
    formatRouteUrl({ view: 'product', productSlug: 'hoodie-black' }),
    '/product/hoodie-black'
  );

  assert.equal(
    formatRouteUrl({ view: 'drop-detail', dropIdentifier: 'drop-1' }),
    '/drops/drop-1'
  );

  assert.equal(formatRouteUrl({ view: 'drops' }), '/drops');
  assert.equal(formatRouteUrl({ view: 'cart' }), '/cart');
  assert.equal(formatRouteUrl({ view: 'checkout' }), '/checkout');
  assert.equal(
    formatRouteUrl({ view: 'payment-return', orderId: 'ord-1' }),
    '/payment/return?order_id=ord-1'
  );
  assert.equal(formatRouteUrl({ view: 'auth', profileTab: 'orders' }), '/profile/orders');
  assert.equal(formatRouteUrl({ view: 'auth', profileTab: 'wishlist' }), '/profile/wishlist');
  assert.equal(formatRouteUrl({ view: 'order-detail', orderId: 'ord-1' }), '/orders/ord-1');
  assert.equal(formatRouteUrl({ view: 'architecture' }), '/architecture');
  assert.equal(formatRouteUrl({ view: 'dev' }), '/dev');
  assert.equal(formatRouteUrl({ view: 'admin' }), '/admin');
  assert.equal(formatRouteUrl({ view: 'catalog' }), '/');
});
