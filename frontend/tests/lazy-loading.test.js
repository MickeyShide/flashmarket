import assert from 'node:assert/strict';
import test from 'node:test';

import { observeInfiniteScroll } from '../src/hooks/useInfiniteScroll.js';
import { mergeUniqueByKey, normalizePage } from '../src/hooks/usePaginatedResource.js';

test('infinite scroll requests one page per observer instance', () => {
  const originalObserver = globalThis.IntersectionObserver;
  const target = {};
  let callback;
  let observedTarget;
  let disconnected = false;
  let calls = 0;

  globalThis.IntersectionObserver = class {
    constructor(nextCallback, options) {
      callback = nextCallback;
      assert.equal(options.rootMargin, '300px 0px');
    }

    observe(nextTarget) {
      observedTarget = nextTarget;
    }

    disconnect() {
      disconnected = true;
    }
  };

  try {
    const cleanup = observeInfiniteScroll({
      target,
      hasMore: true,
      isLoading: false,
      onLoadMore: () => { calls += 1; },
      rootMargin: '300px 0px'
    });

    assert.equal(observedTarget, target);
    callback([{ isIntersecting: false }]);
    callback([{ isIntersecting: true }]);
    callback([{ isIntersecting: true }]);
    assert.equal(calls, 1);

    cleanup();
    assert.equal(disconnected, true);
  } finally {
    globalThis.IntersectionObserver = originalObserver;
  }
});

test('infinite scroll stays inactive without more data, while loading, or without browser support', () => {
  const originalObserver = globalThis.IntersectionObserver;
  let observers = 0;
  globalThis.IntersectionObserver = class {
    constructor() { observers += 1; }
    observe() {}
    disconnect() {}
  };

  try {
    observeInfiniteScroll({ target: {}, hasMore: false, isLoading: false, onLoadMore() {} });
    observeInfiniteScroll({ target: {}, hasMore: true, isLoading: true, onLoadMore() {} });
    assert.equal(observers, 0);

    delete globalThis.IntersectionObserver;
    assert.doesNotThrow(() => observeInfiniteScroll({
      target: {},
      hasMore: true,
      isLoading: false,
      onLoadMore() {}
    }));
  } finally {
    globalThis.IntersectionObserver = originalObserver;
  }
});

test('paginated records append without duplicate entity IDs', () => {
  const merged = mergeUniqueByKey(
    [{ id: 'one' }, { id: 'two', value: 'old' }],
    [{ id: 'two', value: 'new' }, { id: 'three' }]
  );

  assert.deepEqual(merged, [
    { id: 'one' },
    { id: 'two', value: 'old' },
    { id: 'three' }
  ]);
});

test('page normalization supports API envelopes and legacy arrays', () => {
  assert.deepEqual(normalizePage({ items: [{ id: 1 }], total: 7 }, 0), {
    items: [{ id: 1 }],
    total: 7
  });
  assert.deepEqual(normalizePage([{ id: 2 }], 5), {
    items: [{ id: 2 }],
    total: 6
  });
});
