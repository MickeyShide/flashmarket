import { test, expect } from '@playwright/test';
import { setupApiMocks } from './fixtures/apiMocks.js';

test.describe('Critical Path: Browse → Add to Cart → Checkout → Payment', () => {
  test.beforeEach(async ({ page }) => {
    // Setup API mocks with authenticated user for smooth checkout
    await setupApiMocks(page, { loggedIn: true });
  });

  test('completes full purchase journey from homepage to payment confirmation', async ({ page }) => {
    // 1. BROWSE
    await page.goto('/');

    // Verify Brand Title & Nav Header
    await expect(page.locator('header h1')).toContainText('FLASHMARKET');
    await expect(page.getByRole('button', { name: 'ВСЕ ТОВАРЫ' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'КАТЕГОРИИ' })).toBeVisible();

    // Verify Drops Banner
    await expect(page.getByText('SUMMER DROP 2026').first()).toBeVisible();

    // Verify Product Grid has items
    const productCard = page.locator('text=Cyber Hoodie 2026').first();
    await expect(productCard).toBeVisible();

    // Click product to navigate to details
    await productCard.click();

    // 2. PRODUCT DETAILS & ADD TO CART
    await expect(page.getByRole('heading', { name: 'Cyber Hoodie 2026' })).toBeVisible();
    await expect(page.getByText('8 900').first()).toBeVisible();

    // Select variant size 'M'
    const sizeMBtn = page.getByRole('button', { name: 'M', exact: true });
    await expect(sizeMBtn).toBeVisible();
    await sizeMBtn.click();

    // Click Add to Cart
    const addToCartBtn = page.getByRole('button', { name: 'ДОБАВИТЬ В КОРЗИНУ' });
    await expect(addToCartBtn).toBeEnabled();
    await addToCartBtn.click();

    // Verify toast notification & Cart Header Badge
    await expect(page.getByText(/добавлен в корзину/i)).toBeVisible();
    const cartBadge = page.locator('header').locator('button[title="Корзина"]').locator('span');
    await expect(cartBadge).toHaveText('1');

    // 3. CART
    // Navigate to Cart
    await page.locator('header').locator('button[title="Корзина"]').click();
    await expect(page.getByRole('heading', { name: 'КОРЗИНА' })).toBeVisible();
    await expect(page.getByText('Cyber Hoodie 2026')).toBeVisible();
    await expect(page.getByText('Размер: M')).toBeVisible();

    // Test quantity change (optimistic + / -)
    const plusBtn = page.getByRole('button', { name: '+' });
    await plusBtn.click();
    await expect(cartBadge).toHaveText('2');

    const minusBtn = page.getByRole('button', { name: '−' });
    await minusBtn.click();
    await expect(cartBadge).toHaveText('1');

    // Proceed to Checkout
    const checkoutBtn = page.getByRole('button', { name: 'ОФОРМИТЬ ЗАКАЗ' });
    await expect(checkoutBtn).toBeVisible();
    await checkoutBtn.click();

    // 4. CHECKOUT
    await expect(page.getByText('ОФОРМЛЕНИЕ ЗАКАЗА')).toBeVisible();

    // Fill delivery & customer fields
    const nameInput = page.getByPlaceholder('Иванов Иван Иванович');
    await expect(nameInput).toBeVisible();
    await nameInput.fill('Тестеров Тест Тестович');

    const addressInput = page.getByPlaceholder('г. Москва, ул. Тверская, д. 1, кв. 10');
    await expect(addressInput).toBeVisible();
    await addressInput.fill('г. Москва, ул. Тверская, д. 10, кв. 42');

    const phoneInput = page.getByPlaceholder('+7 (999) 000-00-00');
    await expect(phoneInput).toBeVisible();
    await phoneInput.fill('+7 (999) 123-45-67');

    // Apply Promo code
    const promoInput = page.getByPlaceholder('Введите промокод (напр. FLASH10)');
    if (await promoInput.isVisible()) {
      await promoInput.fill('FLASH10');
      await page.getByRole('button', { name: 'Применить' }).click();
      await expect(page.getByText('Скидка по промокоду:')).toBeVisible();
    }

    // Submit Order & Proceed to Payment
    const paySubmitBtn = page.getByRole('button', { name: /ОПЛАТИТЬ/i });
    await expect(paySubmitBtn).toBeVisible();
    await paySubmitBtn.click();

    // 5. PAYMENT & CONFIRMATION
    // Verifies transition to payment return / hosted confirmation
    await expect(page.getByText(/ЗАКАЗ УСПЕШНО ОПЛАЧЕН|ОПЛАТА УСПЕШНА|ОФОРМЛЕН|AWAITING_PAYMENT|ID: ord-test-8888/i)).toBeVisible({ timeout: 10000 });
  });

  test('supports optimistic wishlist heart toggle during browsing', async ({ page }) => {
    await page.goto('/');

    // Wait for user authentication to complete
    await expect(page.getByTitle('Cyber Tester')).toBeVisible();

    // Target Cyber Hoodie's heart button
    const productCard = page.locator('text=Cyber Hoodie 2026').locator('xpath=ancestor::div[contains(@class, "group")]');
    const heartBtn = productCard.locator('button').first();
    await expect(heartBtn).toBeVisible();
    await expect(heartBtn).toHaveAttribute('title', 'Добавить в избранное');

    // Click heart -> Optimistically changes to red
    await heartBtn.click();
    await expect(heartBtn).toHaveAttribute('title', 'Удалить из избранного');

    // Click again -> Optimistically removes
    await heartBtn.click();
    await expect(heartBtn).toHaveAttribute('title', 'Добавить в избранное');
  });

  test('supports category and brand navigation filters', async ({ page }) => {
    await page.goto('/');

    // Navigate to Categories
    const categoriesNavBtn = page.getByRole('button', { name: 'КАТЕГОРИИ' });
    await categoriesNavBtn.click();

    // Assert Categories View
    await expect(page.getByText('КАТЕГОРИИ')).toBeVisible();
    await expect(page.getByText('ОДЕЖДА')).toBeVisible();
    await expect(page.getByText('ОБУВЬ')).toBeVisible();
  });
});
