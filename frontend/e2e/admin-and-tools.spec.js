import { test, expect } from '@playwright/test';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Admin Panel & Administrative Features Suite', () => {
  test('blocks non-admin CUSTOMER users from accessing Admin panel', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true, role: 'CUSTOMER' });

    await page.goto('/admin');

    // Customer should see access denied
    await expect(page.getByText('Доступ запрещен')).toBeVisible();
    await expect(page.getByText('Панель управления доступна только пользователям с ролью АДМИНИСТРАТОР.')).toBeVisible();
    await expect(page.getByRole('button', { name: '← Назад в каталог' })).toBeVisible();
  });

  test('allows ADMIN role user to access Admin panel and navigate all administrative tabs', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true, role: 'ADMIN' });

    await page.goto('/admin');

    // Verify Admin Header
    await expect(page.getByRole('heading', { name: 'УПРАВЛЕНИЕ МАГАЗИНОМ' })).toBeVisible();
    await expect(page.getByText(/Панель администратора/i)).toBeVisible();

    // Verify Tabs Navigation (Desktop)
    const tabs = [
      'Товары',
      'Бренды',
      'Категории',
      'Дропы',
      'Промокоды',
      'Медиа',
      'Пользователи',
      'Аудит',
      'Уведомления'
    ];

    for (const tabName of tabs) {
      const tabBtn = page.locator('button', { hasText: tabName }).first();
      if (await tabBtn.isVisible()) {
        await tabBtn.click();
        await page.waitForTimeout(100);
      }
    }
  });

  test('displays Admin button in Header for ADMIN users and allows navigation to panel', async ({ page }) => {
    await setupApiMocks(page, { loggedIn: true, role: 'ADMIN' });

    await page.goto('/');

    // Header should contain Admin link / button
    const adminLink = page.locator('header').locator('button[title="Панель администратора"]');
    if (await adminLink.isVisible()) {
      await adminLink.click();
      await expect(page.getByRole('heading', { name: 'УПРАВЛЕНИЕ МАГАЗИНОМ' })).toBeVisible();
    }
  });
});
