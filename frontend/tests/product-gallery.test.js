import assert from 'node:assert/strict';
import test from 'node:test';

import { buildProductGallery } from '../src/components/Product/productGallery.js';

test('product gallery puts the cover first and sorts the remaining images', () => {
  const gallery = buildProductGallery(' /cover.jpg ', [
    { id: 'late', url: '/late.jpg', sort_order: 20 },
    { id: 'early', url: '/early.jpg', sort_order: 10 }
  ]);

  assert.deepEqual(gallery.map(image => image.url), [
    '/cover.jpg',
    '/early.jpg',
    '/late.jpg'
  ]);
  assert.equal(gallery[0].isCover, true);
  assert.equal(gallery[1].isCover, false);
});

test('product gallery removes duplicate and empty URLs without mutating images', () => {
  const images = [
    { id: 'cover-copy', url: '/cover.jpg', sort_order: 2 },
    { id: 'empty', url: '   ', sort_order: 1 },
    { id: 'gallery', url: '/gallery.jpg', sort_order: 3 }
  ];
  const originalOrder = images.map(image => image.id);

  const gallery = buildProductGallery('/cover.jpg', images);

  assert.deepEqual(gallery.map(image => image.url), ['/cover.jpg', '/gallery.jpg']);
  assert.deepEqual(images.map(image => image.id), originalOrder);
});

test('product gallery supports gallery-only and empty products', () => {
  assert.deepEqual(
    buildProductGallery(null, [{ id: 'gallery', url: '/gallery.jpg' }]).map(image => image.url),
    ['/gallery.jpg']
  );
  assert.deepEqual(buildProductGallery(null, null), []);
});
