import {
  mockUser,
  mockAdminUser,
  mockCategories,
  mockBrands,
  mockProducts,
  mockDrops,
  mockStock,
  mockPromocodes
} from './mockData.js';

/**
 * Sets up robust route mocks for backend APIs in Playwright tests
 */
export async function setupApiMocks(page, options = {}) {
  const { loggedIn = false, role = 'CUSTOMER', user } = options;
  const activeUser = user || (role === 'ADMIN' ? mockAdminUser : mockUser);

  if (loggedIn) {
    await page.addInitScript(() => {
      window.localStorage.setItem('fm_access_token', 'mock-access-token-12345');
    });
  }

  let currentWishedIds = new Set();
  let createdOrders = [
    {
      id: 'ord-test-8888',
      product_name: 'Cyber Hoodie 2026',
      quantity: 1,
      price: 890000,
      original_price: 890000,
      discount_amount: 89000,
      final_price: 801000,
      currency: 'RUB',
      status: 'AWAITING_PAYMENT',
      variant_sku: 'CYBER-H-M',
      variant_size: 'M',
      created_at: new Date().toISOString(),
      payment_expires_at: new Date(Date.now() + 900000).toISOString(),
    }
  ];

  // Auth & Users
  await page.route(/\/users(\/.*|\?.*|$)/, async (route) => {
    if (loggedIn) {
      await route.fulfill({ status: 200, json: activeUser, headers: { 'content-type': 'application/json' } });
    } else {
      await route.fulfill({ status: 401, json: { detail: 'Unauthorized' }, headers: { 'content-type': 'application/json' } });
    }
  });

  await page.route(/\/auth\/login(\/.*|\?.*|$)/, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        tokens: { access_token: 'mock-access-token-12345' },
        user: mockUser
      },
      headers: { 'content-type': 'application/json' }
    });
  });

  await page.route(/\/sessions(\/.*|\?.*|$)/, async (route) => {
    await route.fulfill({ status: 200, json: [], headers: { 'content-type': 'application/json' } });
  });

  // Categories & Brands
  await page.route(/\/api\/v1\/categories(\/.*|\?.*|$)/, async (route) => {
    await route.fulfill({ status: 200, json: mockCategories, headers: { 'content-type': 'application/json' } });
  });

  await page.route(/\/api\/v1\/brands(\/.*|\?.*|$)/, async (route) => {
    await route.fulfill({ status: 200, json: mockBrands, headers: { 'content-type': 'application/json' } });
  });

  // Drops
  await page.route(/\/api\/v1\/drops(\/.*|\?.*|$)/, async (route) => {
    const url = route.request().url();
    const pathname = new URL(url).pathname;

    if (pathname.endsWith('/active')) {
      await route.fulfill({ status: 200, json: mockDrops, headers: { 'content-type': 'application/json' } });
    } else if (pathname.endsWith('/upcoming')) {
      await route.fulfill({ status: 200, json: [], headers: { 'content-type': 'application/json' } });
    } else {
      const parts = pathname.split('/').filter(Boolean);
      const slug = parts[parts.length - 1];
      const match = mockDrops.find(d => d.slug === slug || d.id === slug) || mockDrops[0];
      await route.fulfill({ status: 200, json: match, headers: { 'content-type': 'application/json' } });
    }
  });

  // Stocks
  await page.route(/\/api\/v1\/stocks(\/.*|\?.*|$)/, async (route) => {
    const url = route.request().url();
    const pathname = new URL(url).pathname;

    if (pathname.includes('/reserve')) {
      await route.fulfill({
        status: 200,
        json: {
          id: 'res-test-999',
          reservation: {
            id: 'res-test-999',
            expires_at: new Date(Date.now() + 900000).toISOString()
          },
          expires_at: new Date(Date.now() + 900000).toISOString()
        },
        headers: { 'content-type': 'application/json' }
      });
    } else {
      await route.fulfill({ status: 200, json: mockStock, headers: { 'content-type': 'application/json' } });
    }
  });

  // Promocodes
  await page.route(/\/api\/v1\/promocodes(\/.*|\?.*|$)/, async (route) => {
    const body = route.request().postDataJSON() || {};
    const code = (body.code || '').toUpperCase();
    if (code === 'FLASH10') {
      await route.fulfill({
        status: 200,
        json: {
          valid: true,
          promocode: mockPromocodes.FLASH10,
          discount_amount: 89000,
          final_amount: 801000,
          discount_type: 'PERCENTAGE',
          discount_value: 10
        },
        headers: { 'content-type': 'application/json' }
      });
    } else {
      await route.fulfill({
        status: 400,
        json: { detail: 'Промокод не найден' },
        headers: { 'content-type': 'application/json' }
      });
    }
  });

  // Wishlist
  await page.route(/\/api\/v1\/wishlist(\/.*|\?.*|$)/, async (route) => {
    const method = route.request().method();
    if (method === 'POST') {
      const data = route.request().postDataJSON() || {};
      if (data.product_id) currentWishedIds.add(data.product_id);
      await route.fulfill({ status: 201, json: { success: true }, headers: { 'content-type': 'application/json' } });
    } else if (method === 'DELETE') {
      const url = route.request().url();
      const pid = url.split('/').pop().split('?')[0];
      currentWishedIds.delete(pid);
      await route.fulfill({ status: 200, json: { success: true }, headers: { 'content-type': 'application/json' } });
    } else {
      const items = Array.from(currentWishedIds).map(id => ({ product_id: id }));
      await route.fulfill({ status: 200, json: { items, total: items.length }, headers: { 'content-type': 'application/json' } });
    }
  });

  // Orders
  await page.route(/\/api\/v1\/orders(\/.*|\?.*|$)/, async (route) => {
    const url = route.request().url();
    const pathname = new URL(url).pathname;
    const method = route.request().method();

    if (method === 'POST') {
      await route.fulfill({
        status: 201,
        json: {
          orders: [
            {
              id: 'ord-test-8888',
              product_id: 'prod-cyber-hoodie',
              quantity: 1,
              final_price: 801000,
              currency: 'RUB',
              status: 'AWAITING_PAYMENT'
            }
          ]
        },
        headers: { 'content-type': 'application/json' }
      });
    } else if (pathname.includes('/users/')) {
      await route.fulfill({
        status: 200,
        json: { items: createdOrders, total: createdOrders.length },
        headers: { 'content-type': 'application/json' }
      });
    } else {
      await route.fulfill({
        status: 200,
        json: createdOrders[0],
        headers: { 'content-type': 'application/json' }
      });
    }
  });

  // Payments
  await page.route(/\/api\/v1\/payments(\/.*|\?.*|$)/, async (route) => {
    const url = route.request().url();
    const pathname = new URL(url).pathname;

    if (pathname.includes('/checkout')) {
      await route.fulfill({
        status: 200,
        json: {
          confirmation_url: 'http://localhost:3000/payment/return?order_id=ord-test-8888',
          preparation_status: 'succeeded'
        },
        headers: { 'content-type': 'application/json' }
      });
    } else {
      await route.fulfill({
        status: 200,
        json: {
          id: 'pay-test-1',
          order_id: 'ord-test-8888',
          status: 'PAID',
          current_attempt_status: 'SUCCEEDED'
        },
        headers: { 'content-type': 'application/json' }
      });
    }
  });

  // Products
  await page.route(/\/api\/v1\/products(\/.*|\?.*|$)/, async (route) => {
    const url = route.request().url();
    const pathname = new URL(url).pathname;
    const parts = pathname.split('/').filter(Boolean);
    const slug = parts[parts.length - 1];

    if (slug === 'batch') {
      await route.fulfill({ status: 200, json: { items: mockProducts, total: mockProducts.length }, headers: { 'content-type': 'application/json' } });
    } else if (slug && slug !== 'products' && slug !== 'v1') {
      const match = mockProducts.find(p => p.slug === slug || p.id === slug) || mockProducts[0];
      await route.fulfill({ status: 200, json: match, headers: { 'content-type': 'application/json' } });
    } else {
      await route.fulfill({
        status: 200,
        json: {
          items: mockProducts,
          total: mockProducts.length,
          limit: 20,
          offset: 0
        },
        headers: { 'content-type': 'application/json' }
      });
    }
  });

  // Notifications & Media
  await page.route(/\/api\/v1\/notifications(\/.*|\?.*|$)/, async (route) => {
    await route.fulfill({ status: 200, json: [], headers: { 'content-type': 'application/json' } });
  });

  await page.route(/\/api\/v1\/media(\/.*|\?.*|$)/, async (route) => {
    await route.fulfill({ status: 200, json: [], headers: { 'content-type': 'application/json' } });
  });
}
