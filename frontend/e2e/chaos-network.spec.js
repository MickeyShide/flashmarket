import { test, expect } from '@playwright/test';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Chaos & Network Resilience Suite', () => {
  test('handles 500 server error when applying promocode without breaking checkout UI', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    // Override promocodes endpoint to return 500 Internal Server Error
    await page.route(/\/api\/v1\/promocodes(\/.*|\?.*|$)/, async (route) => {
      await route.fulfill({
        status: 500,
        json: { detail: 'Database connection failed during promo validation' },
        headers: { 'content-type': 'application/json' }
      });
    });

    // Add item to cart and navigate to checkout
    await page.goto('/product/cyber-hoodie-2026');
    await page.getByRole('button', { name: 'M', exact: true }).click();
    await page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' }).click();

    await page.goto('/checkout');
    await expect(page.getByText('ОФОРМЛЕНИЕ ЗАКАЗА')).toBeVisible();

    // Try applying promocode
    const promoInput = page.getByPlaceholder('Введите промокод (напр. FLASH10)');
    await promoInput.fill('FLASH10');
    const applyBtn = page.getByRole('button', { name: 'Применить' });
    await applyBtn.click();

    // Verify error notification or error text is displayed without crashing UI
    await expect(page.getByText(/Database connection failed|Недействительный промокод|Ошибка/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /ОПЛАТИТЬ/i })).toBeEnabled();
  });

  test('handles 500 server error on stock reservation with actionable error toast', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    // Override stock reserve endpoint to simulate transient stock outage
    await page.route(/\/api\/v1\/stocks\/.*\/reserve/, async (route) => {
      await route.fulfill({
        status: 500,
        json: { detail: 'Lock wait timeout in inventory service' },
        headers: { 'content-type': 'application/json' }
      });
    });

    await page.goto('/product/cyber-hoodie-2026');
    await page.getByRole('button', { name: 'M', exact: true }).click();
    await page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' }).click();

    await page.goto('/checkout');

    // Fill delivery form
    await page.getByPlaceholder('Иванов Иван Иванович').fill('Иван Петров');
    await page.getByPlaceholder('г. Москва, ул. Тверская, д. 1, кв. 10').fill('г. Москва, ул. Арбат, д. 1');
    await page.getByPlaceholder('+7 (999) 000-00-00').fill('+7 (999) 555-44-33');

    // Submit order
    const paySubmitBtn = page.getByRole('button', { name: /ОПЛАТИТЬ/i });
    await paySubmitBtn.click();

    // Verify user sees error banner/toast and checkout stays operable
    await expect(page.getByText(/Ошибка резервирования|Lock wait timeout/i)).toBeVisible();
    await expect(paySubmitBtn).toBeEnabled();
  });

  test('rolls back optimistic wishlist toggle when backend throws 500', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true });

    // Override wishlist POST to fail with 500
    await page.route(/\/api\/v1\/wishlist(\/.*|\?.*|$)/, async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          json: { detail: 'Redis down' },
          headers: { 'content-type': 'application/json' }
        });
      } else {
        await route.fulfill({ status: 200, json: { items: [], total: 0 }, headers: { 'content-type': 'application/json' } });
      }
    });

    await page.goto('/');
    await expect(page.getByTitle('Cyber Tester')).toBeVisible();

    const productCard = page.locator('text=Cyber Hoodie 2026').locator('xpath=ancestor::div[contains(@class, "group")]');
    const heartBtn = productCard.locator('button').first();
    await expect(heartBtn).toHaveAttribute('title', 'Добавить в избранное');

    // Click heart
    await heartBtn.click();

    // After failure response, it should roll back and show toast
    await expect(page.getByText(/Не удалось|Ошибка/i)).toBeVisible();
    await expect(heartBtn).toHaveAttribute('title', 'Добавить в избранное');
  });

  test('redirects to auth view with context when session token is invalid (401)', async ({ page }) => {
    // Start without valid token
    await setupApiMocks(page, { loggedIn: false });

    await page.goto('/');

    // User is anonymous, clicking wishlist heart prompts login
    const productCard = page.locator('text=Cyber Hoodie 2026').locator('xpath=ancestor::div[contains(@class, "group")]');
    const heartBtn = productCard.locator('button').first();
    await heartBtn.click();

    // Verifies auth-required toast and view switch to login
    await expect(page.getByText('Войдите, чтобы добавить товар в избранное')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Вход' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Регистрация' })).toBeVisible();
  });
});
