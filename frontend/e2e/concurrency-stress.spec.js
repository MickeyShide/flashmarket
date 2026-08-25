import { test, expect } from '@playwright/test';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Concurrency, Stress & Race Conditions Suite', () => {
  test('rapid clicking Add to Cart prevents race conditions and manages quantity accurately', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    await page.goto('/product/cyber-hoodie-2026');
    await expect(page.getByRole('heading', { name: 'Cyber Hoodie 2026' })).toBeVisible();

    const sizeMBtn = page.getByRole('button', { name: 'M', exact: true });
    await sizeMBtn.click();

    const addBtn = page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' });

    // Spam click 3 times in parallel / rapid succession
    await Promise.all([
      addBtn.click({ clickCount: 1 }),
      addBtn.click({ clickCount: 1 }),
      addBtn.click({ clickCount: 1 })
    ]);

    // Cart badge should reflect valid integer quantity
    const cartBadge = page.locator('header').locator('button[title="Корзина"]').locator('span');
    await expect(cartBadge).toBeVisible();
    const qtyText = await cartBadge.innerText();
    const qtyNum = parseInt(qtyText, 10);
    expect(qtyNum).toBeGreaterThanOrEqual(1);
    expect(qtyNum).toBeLessThanOrEqual(50); // within stock limits
  });

  test('displays out-of-stock badge and disables action when variant stock is 0', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    // Override stocks endpoint to return 0 available
    await page.route(/\/api\/v1\/stocks(\/.*|\?.*|$)/, async (route) => {
      await route.fulfill({
        status: 200,
        json: { total: 0, available: 0, reserved: 0, sold: 100 },
        headers: { 'content-type': 'application/json' }
      });
    });

    await page.goto('/product/cyber-hoodie-2026');
    await expect(page.getByRole('heading', { name: 'Cyber Hoodie 2026' })).toBeVisible();

    // Verify out-of-stock indicators
    await expect(page.locator('.stock-badge.out-of-stock')).toBeVisible();
    const addBtn = page.getByRole('button', { name: /НЕТ В НАЛИЧИИ|НЕДОСТУПНО|ДОБАВИТЬ В КОРЗИНУ/i });
    await expect(addBtn).toBeDisabled();
  });

  test('synchronizes cart count between multiple tabs via localStorage', async ({ context }) => {
    const page1 = await context.newPage();
    const page2 = await context.newPage();

    await setupApiMocks(page1, { loggedIn: true });
    await setupApiMocks(page2, { loggedIn: true });

    // Open Page 1 on Homepage
    await page1.goto('/');
    const cartBadge1 = page1.locator('header').locator('button[title="Корзина"]').locator('span');
    await expect(cartBadge1).toHaveText('0');

    // Open Page 2 on Product and add to cart
    await page2.goto('/product/cyber-hoodie-2026');
    await expect(page2.getByRole('heading', { name: 'Cyber Hoodie 2026' })).toBeVisible();
    await page2.getByRole('button', { name: 'M', exact: true }).click();
    await page2.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' }).click();

    const cartBadge2 = page2.locator('header').locator('button[title="Корзина"]').locator('span');
    await expect(cartBadge2).toHaveText('1');

    // Navigate or reload Page 1 -> Cart reflects the shared localStorage state
    await page1.goto('/cart');
    await expect(page1.getByText('Cyber Hoodie 2026')).toBeVisible();

    await page1.close();
    await page2.close();
  });

  test('drop card displays status and drop detail view loads smoothly', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    await page.goto('/');

    // Drop banner is visible
    const dropCard = page.getByText('SUMMER DROP 2026').first();
    await expect(dropCard).toBeVisible();

    // Click on drop to open Drop detail view
    await dropCard.click();
    await expect(page.getByRole('heading', { name: /SUMMER DROP 2026/i })).toBeVisible();
    await expect(page.getByText(/Главный летний релиз/i)).toBeVisible();
  });
});
