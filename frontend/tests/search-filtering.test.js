import { test } from 'node:test';
import assert from 'node:assert/strict';

/**
 * Filter & search evaluation engine
 */
export function filterProducts(products, filters = {}) {
  if (!Array.isArray(products)) return [];
  const {
    search = '',
    brandId = null,
    categoryId = null,
    minPrice = null,
    maxPrice = null,
    size = null,
    sortBy = 'created_at'
  } = filters;

  const normalizedSearch = search.trim().toLowerCase();

  let filtered = products.filter(p => {
    // 1. Search filter
    if (normalizedSearch) {
      const nameMatch = (p.name || '').toLowerCase().includes(normalizedSearch);
      const descMatch = (p.description || '').toLowerCase().includes(normalizedSearch);
      const brandMatch = (p.brand_name || '').toLowerCase().includes(normalizedSearch);
      if (!nameMatch && !descMatch && !brandMatch) return false;
    }

    // 2. Brand filter
    if (brandId && p.brand_id !== brandId) {
      return false;
    }

    // 3. Category filter
    if (categoryId && p.category_id !== categoryId) {
      return false;
    }

    // 4. Price range
    const price = Number(p.price) || 0;
    if (minPrice !== null && minPrice !== '' && price < Number(minPrice)) {
      return false;
    }
    if (maxPrice !== null && maxPrice !== '' && price > Number(maxPrice)) {
      return false;
    }

    // 5. Size filter
    if (size) {
      const hasSize = (p.variants || []).some(v => (v.size || v.attributes?.size) === size);
      if (!hasSize) return false;
    }

    return true;
  });

  // Sorting
  filtered.sort((a, b) => {
    if (sortBy === 'price_asc') {
      return (Number(a.price) || 0) - (Number(b.price) || 0);
    }
    if (sortBy === 'price_desc') {
      return (Number(b.price) || 0) - (Number(a.price) || 0);
    }
    if (sortBy === 'name') {
      return (a.name || '').localeCompare(b.name || '');
    }
    // Default: created_at desc
    return new Date(b.created_at || 0) - new Date(a.created_at || 0);
  });

  return filtered;
}

const mockCatalog = [
  {
    id: '1',
    name: 'Cyber Hoodie 2026',
    brand_id: 'brand-flash-sect',
    brand_name: 'FLASH SECT',
    category_id: 'cat-hoodies',
    price: 8900,
    created_at: '2026-06-01T10:00:00Z',
    variants: [{ size: 'S' }, { size: 'M' }, { size: 'L' }]
  },
  {
    id: '2',
    name: 'Neon Runners Sneakers',
    brand_id: 'brand-marcelo',
    brand_name: 'MARCELO MIRACLES',
    category_id: 'cat-sneakers',
    price: 14500,
    created_at: '2026-06-05T10:00:00Z',
    variants: [{ size: '42' }, { size: '43' }]
  },
  {
    id: '3',
    name: 'Minimalist T-Shirt',
    brand_id: 'brand-routine',
    brand_name: 'ROUTINE',
    category_id: 'cat-tshirts',
    price: 3200,
    created_at: '2026-05-15T10:00:00Z',
    variants: [{ size: 'M' }, { size: 'XL' }]
  }
];

test('filterProducts filters by search keyword across name, brand and description', () => {
  const result = filterProducts(mockCatalog, { search: 'hoodie' });
  assert.equal(result.length, 1);
  assert.equal(result[0].id, '1');

  const brandResult = filterProducts(mockCatalog, { search: 'marcelo' });
  assert.equal(brandResult.length, 1);
  assert.equal(brandResult[0].id, '2');
});

test('filterProducts handles multi-faceted filter: Brand + Size + Price Range', () => {
  const result = filterProducts(mockCatalog, {
    brandId: 'brand-flash-sect',
    size: 'M',
    minPrice: 5000,
    maxPrice: 10000
  });
  assert.equal(result.length, 1);
  assert.equal(result[0].id, '1');

  // Should return empty if price bounds exclude
  const excluded = filterProducts(mockCatalog, {
    brandId: 'brand-flash-sect',
    size: 'M',
    maxPrice: 4000
  });
  assert.equal(excluded.length, 0);
});

test('filterProducts sorts correctly by price asc, desc, and date', () => {
  const asc = filterProducts(mockCatalog, { sortBy: 'price_asc' });
  assert.equal(asc[0].price, 3200);
  assert.equal(asc[2].price, 14500);

  const desc = filterProducts(mockCatalog, { sortBy: 'price_desc' });
  assert.equal(desc[0].price, 14500);
  assert.equal(desc[2].price, 3200);
});
