import assert from 'node:assert/strict';
import test from 'node:test';

import {
  prefetchData,
  getPrefetchEntry,
  setPrefetchEntry,
  invalidatePrefetch,
  prefetchProduct,
  prefetchDrop,
  prefetchCategories,
  prefetchOrder
} from '../src/services/prefetch.js';

test('prefetchData caches response and returns cached data on subsequent calls', async () => {
  invalidatePrefetch();
  let fetchCount = 0;
  const mockFetch = async (url) => {
    fetchCount += 1;
    return { url, name: 'Test Product' };
  };

  const first = await prefetchData('/api/v1/products/item-1', mockFetch);
  assert.equal(fetchCount, 1);
  assert.deepEqual(first, { url: '/api/v1/products/item-1', name: 'Test Product' });

  const second = await prefetchData('/api/v1/products/item-1', mockFetch);
  assert.equal(fetchCount, 1); // Should not call fetchFn again
  assert.deepEqual(second, { url: '/api/v1/products/item-1', name: 'Test Product' });
});

test('prefetchData joins in-flight promises to avoid duplicate parallel requests', async () => {
  invalidatePrefetch();
  let fetchCount = 0;
  const mockFetch = async (url) => {
    fetchCount += 1;
    await new Promise(r => setTimeout(r, 20));
    return { id: 123, status: 'ok' };
  };

  const [res1, res2] = await Promise.all([
    prefetchData('/api/v1/test-parallel', mockFetch),
    prefetchData('/api/v1/test-parallel', mockFetch)
  ]);

  assert.equal(fetchCount, 1);
  assert.deepEqual(res1, { id: 123, status: 'ok' });
  assert.deepEqual(res2, { id: 123, status: 'ok' });
});

test('invalidatePrefetch clears all or specific cache entries', async () => {
  invalidatePrefetch();
  setPrefetchEntry('/api/v1/products/p1', { data: { id: 'p1' } });
  setPrefetchEntry('/api/v1/products/p2', { data: { id: 'p2' } });
  setPrefetchEntry('/api/v1/categories', { data: [{ id: 'c1' }] });

  assert.notEqual(getPrefetchEntry('/api/v1/products/p1'), null);

  // Invalidate single key
  invalidatePrefetch('/api/v1/products/p1');
  assert.equal(getPrefetchEntry('/api/v1/products/p1'), null);
  assert.notEqual(getPrefetchEntry('/api/v1/products/p2'), null);

  // Invalidate all
  invalidatePrefetch();
  assert.equal(getPrefetchEntry('/api/v1/products/p2'), null);
  assert.equal(getPrefetchEntry('/api/v1/categories'), null);
});

test('entity prefetchers format correct API URLs', async () => {
  invalidatePrefetch();
  const calledUrls = [];
  const mockApiJson = async (url) => {
    calledUrls.push(url);
    return { ok: true };
  };

  prefetchProduct('oversized-hoodie', mockApiJson);
  assert.ok(calledUrls.includes('/api/v1/products/oversized-hoodie'));

  prefetchDrop('summer-drop', mockApiJson);
  assert.ok(calledUrls.includes('/api/v1/drops/summer-drop'));

  const uuid = '123e4567-e89b-12d3-a456-426614174000';
  prefetchDrop(uuid, mockApiJson);
  assert.ok(calledUrls.includes(`/api/v1/drops/id/${uuid}`));

  prefetchCategories(mockApiJson);
  assert.ok(calledUrls.includes('/api/v1/categories'));

  prefetchOrder('order-uuid-999', mockApiJson);
  assert.ok(calledUrls.includes('/api/v1/orders/order-uuid-999'));
});

test('optimistic wishlist state update and rollback on error simulation', async () => {
  let state = new Set(['item-1']);

  const optimisticAdd = async (itemId, shouldFail = false) => {
    const previous = new Set(state);
    state = new Set([...state, itemId]); // Optimistic update

    try {
      if (shouldFail) {
        throw new Error('Network error');
      }
      return true;
    } catch (err) {
      state = previous; // Rollback
      return false;
    }
  };

  // Test successful optimistic addition
  const ok = await optimisticAdd('item-2', false);
  assert.equal(ok, true);
  assert.ok(state.has('item-2'));

  // Test failed optimistic addition with rollback
  const failed = await optimisticAdd('item-3', true);
  assert.equal(failed, false);
  assert.equal(state.has('item-3'), false);
  assert.ok(state.has('item-2'));
});
