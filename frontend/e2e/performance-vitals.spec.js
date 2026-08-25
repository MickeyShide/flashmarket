import { test, expect } from '@playwright/test';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Web Vitals & Performance Suite', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });
  });

  test('measures fast page load and DOMContentLoaded timing on Catalog page', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await expect(page.locator('header h1')).toBeVisible();
    await expect(page.getByText('Cyber Hoodie 2026').first()).toBeVisible();
    const duration = Date.now() - startTime;

    // Fast local rendering benchmark
    expect(duration).toBeLessThan(5000);

    // Browser navigation timing metrics
    const navigationTiming = await page.evaluate(() => {
      const entries = performance.getEntriesByType('navigation');
      if (entries.length > 0) {
        const nav = entries[0];
        return {
          domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
          loadComplete: nav.loadEventEnd - nav.startTime,
        };
      }
      return null;
    });

    if (navigationTiming && navigationTiming.domContentLoaded > 0) {
      expect(navigationTiming.domContentLoaded).toBeLessThan(3500);
    }
  });

  test('verifies low layout shift (CLS) during catalog rendering', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Cyber Hoodie 2026').first()).toBeVisible();

    // Evaluate Layout Shift entries from PerformanceObserver
    const clsScore = await page.evaluate(() => {
      let score = 0;
      const entries = performance.getEntriesByType('layout-shift') || [];
      for (const entry of entries) {
        if (!entry.hadRecentInput) {
          score += entry.value;
        }
      }
      return score;
    });

    // Web Vitals good CLS threshold is < 0.1
    expect(clsScore).toBeLessThan(0.1);
  });

  test('measures fast LCP on Product Detail View', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/product/cyber-hoodie-2026');
    await expect(page.getByRole('heading', { name: 'Cyber Hoodie 2026' })).toBeVisible();
    const duration = Date.now() - startTime;

    expect(duration).toBeLessThan(5000);
  });
});
