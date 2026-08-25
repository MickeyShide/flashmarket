export const mockUser = {
  id: 'usr-test-1234-5678',
  email: 'tester@flashmarket.test',
  full_name: 'Cyber Tester',
  role: 'CUSTOMER',
  is_active: true,
};

export const mockAdminUser = {
  id: 'usr-admin-123',
  email: 'admin@flashmarket.test',
  full_name: 'Lead Admin',
  role: 'ADMIN',
  is_active: true,
};

export const mockCategories = [
  { id: 'cat-1', name: 'ОДЕЖДА', slug: 'clothes', children: [] },
  { id: 'cat-2', name: 'ОБУВЬ', slug: 'shoes', children: [] },
  { id: 'cat-3', name: 'ХУДИ', slug: 'hoodies', parent_id: 'cat-1', children: [] },
  { id: 'cat-4', name: 'АКСЕССУАРЫ', slug: 'accessories', children: [] },
];

export const mockBrands = [
  { id: 'br-1', name: 'CYBERWEAR', slug: 'cyberwear', logo_url: 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=100' },
  { id: 'br-2', name: 'NEONDROP', slug: 'neondrop', logo_url: 'https://images.unsplash.com/photo-1552346154-21d32810aba3?w=100' },
];

export const mockProducts = [
  {
    id: 'prod-cyber-hoodie',
    name: 'Cyber Hoodie 2026',
    slug: 'cyber-hoodie-2026',
    price: 8900,
    currency: 'RUB',
    category_id: 'cat-3',
    category_name: 'ХУДИ',
    brand_id: 'br-1',
    brand_name: 'CYBERWEAR',
    description: 'Лимитированное худи из плотного хлопка с киберпанк графикой.',
    cover_image: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=600&q=80',
    images: [
      { id: 'img-1', url: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=600&q=80', is_cover: true },
      { id: 'img-2', url: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=600&q=80', is_cover: false }
    ],
    variants: [
      { id: 'var-s', product_id: 'prod-cyber-hoodie', size: 'S', color: 'Black', sku: 'CYBER-H-S', is_active: true, effective_price: 8900 },
      { id: 'var-m', product_id: 'prod-cyber-hoodie', size: 'M', color: 'Black', sku: 'CYBER-H-M', is_active: true, effective_price: 8900 },
      { id: 'var-l', product_id: 'prod-cyber-hoodie', size: 'L', color: 'Black', sku: 'CYBER-H-L', is_active: true, effective_price: 8900 }
    ]
  },
  {
    id: 'prod-neon-sneakers',
    name: 'Neon Sneakers X',
    slug: 'neon-sneakers-x',
    price: 14900,
    currency: 'RUB',
    category_id: 'cat-2',
    category_name: 'ОБУВЬ',
    brand_id: 'br-2',
    brand_name: 'NEONDROP',
    description: 'Футуристичные кроссовки с амортизирующей подошвой.',
    cover_image: 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=600&q=80',
    images: [],
    variants: [
      { id: 'var-41', product_id: 'prod-neon-sneakers', size: '41', sku: 'NEON-SNK-41', is_active: true, effective_price: 14900 },
      { id: 'var-42', product_id: 'prod-neon-sneakers', size: '42', sku: 'NEON-SNK-42', is_active: true, effective_price: 14900 }
    ]
  }
];

export const mockDrops = [
  {
    id: 'drop-summer-2026',
    name: 'SUMMER DROP 2026',
    slug: 'summer-drop-2026',
    title: 'SUMMER DROP 2026',
    description: 'Главный летний релиз лимитированной коллекции.',
    status: 'ACTIVE',
    starts_at: '2026-06-01T12:00:00Z',
    ends_at: '2026-09-01T12:00:00Z',
    max_per_user: 2,
    payment_timeout_seconds: 900,
    cover_image: 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=800&q=80',
    items: [
      { product_id: 'prod-cyber-hoodie' },
      { product_id: 'prod-neon-sneakers' }
    ]
  }
];

export const mockStock = {
  total: 20,
  available: 15,
  reserved: 2,
  sold: 3
};

export const mockPromocodes = {
  FLASH10: {
    code: 'FLASH10',
    status: 'ACTIVE',
    discount_type: 'PERCENTAGE',
    discount_value: 10,
    currency: 'RUB',
    min_order_amount: 1000
  }
};
