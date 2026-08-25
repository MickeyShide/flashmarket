import { test, expect } from '@playwright/test';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Responsive Mobile & Tablet Viewport Matrix Suite', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });
  });

  test('mobile viewport (375x667): renders header, product grid and navigation with no horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');

    // Header elements are visible
    await expect(page.locator('header h1')).toBeVisible();
    await expect(page.locator('header').locator('button[title="Корзина"]')).toBeVisible();

    // Verify product card is visible and fits screen
    const productCard = page.locator('text=Cyber Hoodie 2026').first();
    await expect(productCard).toBeVisible();

    // Check no horizontal scroll overflow
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2); // allowing tiny subpixel rounding
  });

  test('mobile viewport (375x667): completes mobile purchase flow (product detail -> size selection -> cart -> checkout)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/product/cyber-hoodie-2026');

    // Product Detail heading & size buttons
    await expect(page.getByRole('heading', { name: 'Cyber Hoodie 2026' })).toBeVisible();
    const sizeBtn = page.getByRole('button', { name: 'M', exact: true });
    await expect(sizeBtn).toBeVisible();
    await sizeBtn.click();

    // Add to Cart
    const addBtn = page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' });
    await addBtn.click();
    await expect(page.getByText(/добавлен в корзину/i)).toBeVisible();

    // Go to Cart
    await page.locator('header').locator('button[title="Корзина"]').click();
    await expect(page.getByRole('heading', { name: 'КОРЗИНА' })).toBeVisible();

    // Checkout
    const checkoutBtn = page.getByRole('button', { name: 'ОФОРМИТЬ ЗАКАЗ' });
    await checkoutBtn.click();
    await expect(page.getByText('ОФОРМЛЕНИЕ ЗАКАЗА')).toBeVisible();
  });

  test('tablet viewport (768x1024): renders grid layout and controls cleanly', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });

    await page.goto('/');

    await expect(page.locator('header h1')).toBeVisible();
    await expect(page.getByText('SUMMER DROP 2026').first()).toBeVisible();
    await expect(page.getByText('Cyber Hoodie 2026').first()).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2);
  });
});
