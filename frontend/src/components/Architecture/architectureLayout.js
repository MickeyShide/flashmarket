/**
 * Architecture Map Layout & Compaction Algorithms
 * Computes deterministic compact coordinates and delta transform offsets
 * for any subset of active nodes in FlashMarket architecture.
 *
 * Supports desktop (wide) and mobile (compact) layout presets.
 */

// Desktop layout — spacious, engineer-grade map
// Canvas: ~920 x 480 — designed for 1:1 or slight scale-down on most screens
export const BASE_NODE_POSITIONS = {
  // Legacy / Test Compatibility (not rendered on map)
  'node-component-browser': { x: 30, y: 130, width: 100, height: 105 },
  'node-component-gateway': { x: 165, y: 130, width: 100, height: 105 },

  // Row 1: Core Services (5 across, wider cards for full names)
  'node-service-auth': { x: 40, y: 40, width: 120, height: 52 },
  'node-service-catalog': { x: 200, y: 40, width: 120, height: 52 },
  'node-service-inventory': { x: 360, y: 40, width: 130, height: 52 },
  'node-service-orders': { x: 530, y: 40, width: 120, height: 52 },
  'node-service-payments': { x: 690, y: 40, width: 130, height: 52 },

  // Row 2: Secondary & Supporting Services
  'node-service-notifications': { x: 115, y: 118, width: 140, height: 52 },
  'node-service-wishlist': { x: 295, y: 118, width: 120, height: 52 },
  'node-service-drops': { x: 455, y: 118, width: 120, height: 52 },
  'node-service-media': { x: 615, y: 118, width: 120, height: 52 },

  // Middle Tier: Async Event Queue & Celery Workers
  'node-component-rabbitmq': { x: 200, y: 215, width: 160, height: 42 },
  'node-component-celery': { x: 470, y: 215, width: 160, height: 42 },

  // Bottom Tier: Storage, Cache, Files & Metrics
  'node-component-postgres': { x: 50, y: 310, width: 145, height: 42 },
  'node-component-redis': { x: 235, y: 310, width: 120, height: 42 },
  'node-component-s3': { x: 395, y: 310, width: 135, height: 42 },
  'node-component-prometheus': { x: 575, y: 310, width: 145, height: 42 },
};

// Mobile layout — compact, vertically stacked for small screens
export const MOBILE_NODE_POSITIONS = {
  'node-component-browser': { x: 10, y: 130, width: 90, height: 90 },
  'node-component-gateway': { x: 120, y: 130, width: 90, height: 90 },

  // Row 1: Core Services (3 per row on mobile)
  'node-service-auth': { x: 15, y: 20, width: 100, height: 50 },
  'node-service-catalog': { x: 130, y: 20, width: 100, height: 50 },
  'node-service-inventory': { x: 245, y: 20, width: 110, height: 50 },

  // Row 2
  'node-service-orders': { x: 15, y: 82, width: 100, height: 50 },
  'node-service-payments': { x: 130, y: 82, width: 110, height: 50 },
  'node-service-notifications': { x: 255, y: 82, width: 120, height: 50 },

  // Row 3
  'node-service-wishlist': { x: 15, y: 144, width: 100, height: 50 },
  'node-service-drops': { x: 130, y: 144, width: 100, height: 50 },
  'node-service-media': { x: 245, y: 144, width: 100, height: 50 },

  // Middle Tier
  'node-component-rabbitmq': { x: 30, y: 218, width: 145, height: 42 },
  'node-component-celery': { x: 195, y: 218, width: 145, height: 42 },

  // Bottom Tier
  'node-component-postgres': { x: 10, y: 280, width: 120, height: 42 },
  'node-component-redis': { x: 140, y: 280, width: 105, height: 42 },
  'node-component-s3': { x: 255, y: 280, width: 110, height: 42 },
  'node-component-prometheus': { x: 140, y: 332, width: 120, height: 42 },
};

export const ALL_SERVICES = [
  'node-service-auth',
  'node-service-catalog',
  'node-service-inventory',
  'node-service-orders',
  'node-service-payments',
  'node-service-notifications',
  'node-service-wishlist',
  'node-service-drops',
  'node-service-media',
];

export const ALL_QUEUES = [
  'node-component-rabbitmq',
  'node-component-celery',
];

export const ALL_DBS = [
  'node-component-postgres',
  'node-component-redis',
  'node-component-s3',
  'node-component-prometheus',
];

/**
 * Returns the appropriate layout positions based on screen width.
 */
export function getPositionsForWidth(width) {
  return width < 768 ? MOBILE_NODE_POSITIONS : BASE_NODE_POSITIONS;
}

/**
 * Returns the bounding box for a given set of positions.
 */
export function getBoundingBoxForPositions(positions) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  Object.values(positions).forEach(({ x, y, width, height }) => {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x + width > maxX) maxX = x + width;
    if (y + height > maxY) maxY = y + height;
  });
  const w = maxX - minX;
  const h = maxY - minY;
  return {
    minX, minY, maxX, maxY,
    width: w,
    height: h,
    centerX: minX + w / 2,
    centerY: minY + h / 2,
  };
}

/**
 * Computes deterministic coordinates and bounding box for FlashMarket architecture.
 * Nodes remain fixed in their natural grid to prevent disorienting jumps and line distortion.
 */
export function computeCompactLayout(isolatedNodes, isMobile = false) {
  const positions = isMobile ? MOBILE_NODE_POSITIONS : BASE_NODE_POSITIONS;
  const offsets = {};
  Object.keys(positions).forEach((id) => {
    offsets[id] = { x: 0, y: 0 };
  });

  const boundingBox = getBoundingBoxForPositions(positions);

  return {
    offsets,
    boundingBox,
  };
}
