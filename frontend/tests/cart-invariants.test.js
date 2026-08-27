import { test } from 'node:test';
import assert from 'node:assert/strict';

/**
 * Pure cart calculations & invariant business rules
 */
export function calculateCartItemTotal(item) {
  if (!item) return 0;
  const price = Math.max(0, Number(item.price) || 0);
  const qty = Math.max(0, parseInt(item.qty, 10) || 0);
  return Math.round(price * qty);
}

export function calculateCartTotal(cartItems) {
  if (!Array.isArray(cartItems)) return 0;
  return cartItems.reduce((acc, item) => acc + calculateCartItemTotal(item), 0);
}

export function applyPromocodeDiscount(rawTotalRub, promo) {
  const rawTotalMinor = Math.round(rawTotalRub * 100);
  if (!promo || !promo.valid) {
    return {
      discountMinor: 0,
      finalTotalMinor: rawTotalMinor,
      discountRub: 0,
      finalTotalRub: rawTotalRub
    };
  }

  let discountMinor = 0;
  if (promo.discount_type === 'PERCENTAGE') {
    const pct = Math.min(100, Math.max(0, Number(promo.discount_value) || 0));
    discountMinor = Math.round((rawTotalMinor * pct) / 100);
  } else if (promo.discount_type === 'FIXED') {
    discountMinor = Math.round(Number(promo.discount_amount) || (Number(promo.discount_value) * 100) || 0);
  }

  // Ensure discount doesn't exceed total amount
  discountMinor = Math.min(discountMinor, rawTotalMinor);
  const finalTotalMinor = Math.max(0, rawTotalMinor - discountMinor);

  return {
    discountMinor,
    finalTotalMinor,
    discountRub: discountMinor / 100,
    finalTotalRub: finalTotalMinor / 100
  };
}

export function validateCartStockLimit(currentCartQty, requestedQty, availableStock) {
  const current = Math.max(0, Number(currentCartQty) || 0);
  const requested = Math.max(1, Number(requestedQty) || 1);
  const available = Math.max(0, Number(availableStock) || 0);

  if (available <= 0) {
    return { allowed: false, reason: 'OUT_OF_STOCK', maxAddable: 0 };
  }
  if (current + requested > available) {
    const maxAddable = Math.max(0, available - current);
    return { allowed: false, reason: 'EXCEEDS_STOCK', maxAddable };
  }
  return { allowed: true, reason: null, maxAddable: requested };
}

test('calculateCartTotal correctly sums multiple items with precision', () => {
  const items = [
    { id: '1', price: 8900, qty: 2 }, // 17800
    { id: '2', price: 14500, qty: 1 }, // 14500
    { id: '3', price: 2990.50, qty: 3 } // 8971.5 -> 8972
  ];

  const total = calculateCartTotal(items);
  assert.equal(total, 17800 + 14500 + 8972);
});

test('calculateCartTotal handles empty or invalid cart data gracefully', () => {
  assert.equal(calculateCartTotal([]), 0);
  assert.equal(calculateCartTotal(null), 0);
  assert.equal(calculateCartTotal(undefined), 0);
  assert.equal(calculateCartTotal([{ price: -500, qty: 2 }]), 0);
  assert.equal(calculateCartTotal([{ price: 1000, qty: -5 }]), 0);
});

test('applyPromocodeDiscount handles percentage discount with strict boundaries', () => {
  const rawTotal = 10000; // 10,000 RUB
  const promo = { valid: true, discount_type: 'PERCENTAGE', discount_value: 15 };

  const result = applyPromocodeDiscount(rawTotal, promo);
  assert.equal(result.discountRub, 1500);
  assert.equal(result.finalTotalRub, 8500);
  assert.equal(result.discountMinor, 150000);
  assert.equal(result.finalTotalMinor, 850000);
});

test('applyPromocodeDiscount caps discount at 100% and prevents negative totals', () => {
  const rawTotal = 5000;
  const promoFixedExcess = { valid: true, discount_type: 'FIXED', discount_amount: 800000 }; // 8,000 RUB > 5,000 RUB

  const result = applyPromocodeDiscount(rawTotal, promoFixedExcess);
  assert.equal(result.discountRub, 5000);
  assert.equal(result.finalTotalRub, 0);
  assert.equal(result.finalTotalMinor, 0);
});

test('validateCartStockLimit prevents overselling when available stock is exhausted', () => {
  // Case 1: Out of stock
  const res1 = validateCartStockLimit(0, 1, 0);
  assert.equal(res1.allowed, false);
  assert.equal(res1.reason, 'OUT_OF_STOCK');

  // Case 2: In cart 3, wants 2 more, available 4
  const res2 = validateCartStockLimit(3, 2, 4);
  assert.equal(res2.allowed, false);
  assert.equal(res2.reason, 'EXCEEDS_STOCK');
  assert.equal(res2.maxAddable, 1);

  // Case 3: In cart 2, wants 2 more, available 5
  const res3 = validateCartStockLimit(2, 2, 5);
  assert.equal(res3.allowed, true);
  assert.equal(res3.maxAddable, 2);
});

test('formatPrice correctly formats large ruble prices without unintended kopecks division', async () => {
  const { formatPrice } = await import('../src/utils/formatters.js');
  // 120,000 RUB as rubles (isKopecks = false)
  const formattedRub = formatPrice(120000, 'RUB', false);
  assert.match(formattedRub, /120[\s\u00A0\u202F]?000[\s\u00A0\u202F]?₽/);

  // 120,000 RUB as kopecks (12,000,000 kopecks, isKopecks = true)
  const formattedKop = formatPrice(12000000, 'RUB', true);
  assert.match(formattedKop, /120[\s\u00A0\u202F]?000[\s\u00A0\u202F]?₽/);
});
