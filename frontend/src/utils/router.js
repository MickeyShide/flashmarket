/**
 * FlashMarket Client-Side SPA Router Utility
 * Parses pathnames into views and converts application state back into clean URLs.
 */

export function parseRoute(
  pathname = (typeof window !== 'undefined' ? window.location.pathname : '/'),
  search = (typeof window !== 'undefined' ? window.location.search : '')
) {
  const path = pathname || '/';

  // 1. Admin Panel
  if (path.startsWith('/admin')) {
    return { view: 'admin' };
  }

  if (path === '/payment/return') {
    const params = new URLSearchParams(search || '');
    return {
      view: 'payment-return',
      orderId: params.get('order_id') || null,
    };
  }

  // 4. Product Details: /product/:slug or /products/:slug
  const productMatch = path.match(/^\/products?\/([^/]+)/);
  if (productMatch) {
    return {
      view: 'product',
      productSlug: decodeURIComponent(productMatch[1]),
    };
  }

  // 5. Drop Details: /drop/:id or /drops/:id (excluding /drops list)
  const dropMatch = path.match(/^\/drops?\/([^/]+)/);
  if (dropMatch && dropMatch[1] !== 'all') {
    return {
      view: 'drop-detail',
      dropIdentifier: decodeURIComponent(dropMatch[1]),
    };
  }

  // 6. Drops Index
  if (path === '/drops') {
    return { view: 'drops' };
  }

  // 7. Categories View
  if (path === '/categories') {
    return { view: 'categories' };
  }

  // 8. Cart
  if (path === '/cart') {
    return { view: 'cart' };
  }

  // 9. Checkout
  if (path === '/checkout') {
    return { view: 'checkout' };
  }

  // 10. Order Details: /order/:id or /orders/:id
  const orderMatch = path.match(/^\/orders?\/([^/]+)/);
  if (orderMatch) {
    return {
      view: 'order-detail',
      orderId: decodeURIComponent(orderMatch[1]),
    };
  }

  // 11. Profile & Auth: /profile, /profile/wishlist, /profile/orders, /profile/notifications, /auth
  if (path.startsWith('/profile') || path.startsWith('/auth')) {
    let profileTab = 'profile';
    if (path.includes('/wishlist')) profileTab = 'wishlist';
    else if (path.includes('/orders')) profileTab = 'orders';
    else if (path.includes('/notifications')) profileTab = 'notifications';
    return {
      view: 'auth',
      profileTab,
    };
  }

  // 12. Default Catalog Home
  return { view: 'catalog' };
}

export function formatRouteUrl({ view, productSlug, dropIdentifier, orderId, profileTab }) {
  switch (view) {
    case 'admin':
      return '/admin';
    case 'product':
      return productSlug ? `/product/${encodeURIComponent(productSlug)}` : '/';
    case 'drop-detail':
      return dropIdentifier ? `/drops/${encodeURIComponent(dropIdentifier)}` : '/drops';
    case 'drops':
      return '/drops';
    case 'categories':
      return '/categories';
    case 'cart':
      return '/cart';
    case 'checkout':
      return '/checkout';
    case 'payment-return':
      return orderId
        ? `/payment/return?order_id=${encodeURIComponent(orderId)}`
        : '/payment/return';
    case 'order-detail':
      return orderId ? `/orders/${encodeURIComponent(orderId)}` : '/profile/orders';
    case 'auth':
      if (profileTab === 'wishlist') return '/profile/wishlist';
      if (profileTab === 'orders') return '/profile/orders';
      if (profileTab === 'notifications') return '/profile/notifications';
      return '/profile';
    case 'catalog':
    default:
      return '/';
  }
}
