import { test, expect } from '@playwright/test';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Edge Cases & Validation Suite', () => {
  test('handles multi-filter matrix combining brand, price range, size, sorting and reset', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    await page.goto('/');

    // 1. Filter by Brand
    const brandSelect = page.locator('select[aria-label="Фильтр по бренду"]');
    await expect(brandSelect).toBeVisible();
    await expect(brandSelect.locator('option[value="br-1"]')).toBeAttached();
    await brandSelect.selectOption({ value: 'br-1' });

    // 2. Filter by Price range
    const minPriceInput = page.locator('input[aria-label="Минимальная цена"]');
    await minPriceInput.fill('5000');

    const maxPriceInput = page.locator('input[aria-label="Максимальная цена"]');
    await maxPriceInput.fill('10000');

    // 3. Filter by Size
    const sizeSelect = page.locator('select[aria-label="Фильтр по размеру"]');
    await sizeSelect.selectOption({ value: 'M' });

    // 4. Sort order
    const sortSelect = page.locator('select[aria-label="Сортировка товаров"]');
    await sortSelect.selectOption({ value: 'price_asc' });

    // 5. Search input
    const searchInput = page.locator('input[aria-label="Поиск по названию товаров"]');
    await searchInput.fill('Cyber');

    // Catalog items should remain visible matching criteria
    await expect(page.getByText('Cyber Hoodie 2026').first()).toBeVisible();

    // Reset Search
    await searchInput.fill('');
    await brandSelect.selectOption({ value: '' });
    await sizeSelect.selectOption({ value: '' });
  });

  test('validates promocodes for invalid codes, lowercase auto-conversion and error hints', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    // Add item to cart
    await page.goto('/product/cyber-hoodie-2026');
    await page.getByRole('button', { name: 'M', exact: true }).click();
    await page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' }).click();

    await page.goto('/checkout');
    await expect(page.getByText('ОФОРМЛЕНИЕ ЗАКАЗА')).toBeVisible();

    const promoInput = page.getByPlaceholder('Введите промокод (напр. FLASH10)');
    const applyBtn = page.getByRole('button', { name: 'Применить' });

    // Case 1: Non-existent promocode
    await promoInput.fill('INVALID999');
    await applyBtn.click();
    await expect(page.getByText(/Промокод не найден|Недействительный промокод/i)).toBeVisible();

    // Case 2: Lowercase code auto-normalized to uppercase
    await promoInput.fill('flash10');
    await applyBtn.click();
    await expect(page.getByText('Скидка по промокоду:')).toBeVisible();

    // Case 3: Remove promocode
    const removeBtn = page.getByRole('button', { name: 'Удалить' });
    await expect(removeBtn).toBeVisible();
    await removeBtn.click();
    await expect(page.getByText('Скидка по промокоду:')).not.toBeVisible();
  });

  test('handles cart item removal down to zero transitioning to empty cart view', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    // Add item to cart
    await page.goto('/product/cyber-hoodie-2026');
    await page.getByRole('button', { name: 'M', exact: true }).click();
    await page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' }).click();

    // Open Cart
    await page.goto('/cart');
    await expect(page.getByText('Cyber Hoodie 2026')).toBeVisible();

    // Click '-' button to decrement to 0 (or remove button)
    const minusBtn = page.getByRole('button', { name: '−' });
    await minusBtn.click();

    // Cart should now show empty state
    await expect(page.getByText(/КОРЗИНА ПУСТА|ВАША КОРЗИНА ПУСТА/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Перейти в каталог' })).toBeVisible();
  });
});
