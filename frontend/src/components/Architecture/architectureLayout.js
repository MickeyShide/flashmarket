export const BASE_NODE_POSITIONS = Object.freeze({
  'node-component-gateway': { x: 360, y: 40, width: 220, height: 96 },
  'node-service-auth': { x: 40, y: 220, width: 180, height: 88 },
  'node-service-orders': { x: 260, y: 220, width: 180, height: 88 },
  'node-service-inventory': { x: 480, y: 220, width: 180, height: 88 },
  'node-service-notifications': { x: 700, y: 220, width: 180, height: 88 },
  'node-service-media': { x: 920, y: 220, width: 180, height: 88 },
  'node-component-rabbitmq': { x: 260, y: 400, width: 220, height: 88 },
  'node-component-postgres': { x: 520, y: 400, width: 220, height: 88 },
  'node-component-s3': { x: 780, y: 400, width: 220, height: 88 },
});

export function getBoundingBoxForPositions(positions) {
  const nodes = Object.values(positions);
  if (nodes.length === 0) return { x: 0, y: 0, width: 0, height: 0 };
  const minX = Math.min(...nodes.map(node => node.x));
  const minY = Math.min(...nodes.map(node => node.y));
  const maxX = Math.max(...nodes.map(node => node.x + node.width));
  const maxY = Math.max(...nodes.map(node => node.y + node.height));
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

export function computeCompactLayout(_isolatedNodeIds, mobile = false) {
  const positions = mobile
    ? Object.fromEntries(Object.entries(BASE_NODE_POSITIONS).map(([id, node], index) => [
      id,
      { ...node, x: 20, y: 20 + index * 120 },
    ]))
    : BASE_NODE_POSITIONS;
  return {
    positions,
    boundingBox: getBoundingBoxForPositions(positions),
    offsets: Object.fromEntries(Object.keys(BASE_NODE_POSITIONS).map(id => [id, { x: 0, y: 0 }])),
  };
}
