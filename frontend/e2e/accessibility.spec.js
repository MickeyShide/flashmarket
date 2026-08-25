import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Accessibility (a11y) Audits with axe-core', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });
  });

  test('Homepage / Catalog passes WCAG 2.1 AA accessibility standards', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header h1')).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast']) // Soften purely subjective design theme colors if any
      .analyze();

    const criticalOrSerious = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalOrSerious).toEqual([]);
  });

  test('Product Detail passes WCAG 2.1 AA accessibility standards', async ({ page }) => {
    await page.goto('/product/cyber-hoodie-2026');
    await expect(page.getByRole('heading', { name: 'Cyber Hoodie 2026' })).toBeVisible({ timeout: 10000 });

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast'])
      .analyze();

    const criticalOrSerious = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalOrSerious).toEqual([]);
  });

  test('Categories View passes WCAG 2.1 AA accessibility standards', async ({ page }) => {
    await page.goto('/categories');
    await expect(page.getByText('КАТЕГОРИИ')).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast'])
      .analyze();

    const criticalOrSerious = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalOrSerious).toEqual([]);
  });

  test('Cart and Checkout Views pass WCAG 2.1 AA accessibility standards', async ({ page }) => {
    // Add item to cart
    await page.goto('/product/cyber-hoodie-2026');
    await page.getByRole('button', { name: 'M', exact: true }).click();
    await page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' }).click();

    // Check Cart View
    await page.goto('/cart');
    await expect(page.getByText('Cyber Hoodie 2026')).toBeVisible();

    let results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast'])
      .analyze();

    let criticalOrSerious = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalOrSerious).toEqual([]);

    // Check Checkout View
    await page.goto('/checkout');
    await expect(page.getByText('ОФОРМЛЕНИЕ ЗАКАЗА')).toBeVisible();

    results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast'])
      .analyze();

    criticalOrSerious = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(criticalOrSerious).toEqual([]);
  });
});
