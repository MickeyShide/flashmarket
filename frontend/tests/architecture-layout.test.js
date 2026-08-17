import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeCompactLayout, BASE_NODE_POSITIONS, getBoundingBoxForPositions } from '../src/components/Architecture/architectureLayout.js';

test('computeCompactLayout returns default positions and valid bounding box for null/empty isolation', () => {
  const result = computeCompactLayout(null);
  const expectedBox = getBoundingBoxForPositions(BASE_NODE_POSITIONS);
  assert.equal(result.boundingBox.width, expectedBox.width);
  assert.equal(result.boundingBox.height, expectedBox.height);
  assert.equal(result.offsets['node-component-gateway'].x, 0);
  assert.equal(result.offsets['node-service-media'].x, 0);
});

test('computeCompactLayout keeps layout stable without card displacement when isolated nodes are passed', () => {
  const isolated = ['node-component-gateway', 'node-service-media', 'node-component-postgres', 'node-component-s3'];
  const result = computeCompactLayout(isolated);

  const expectedBox = getBoundingBoxForPositions(BASE_NODE_POSITIONS);
  assert.equal(result.boundingBox.width, expectedBox.width);
  assert.equal(result.boundingBox.height, expectedBox.height);
  assert.equal(result.offsets['node-service-media'].x, 0);
  assert.equal(result.offsets['node-component-gateway'].x, 0);
});

test('computeCompactLayout preserves grid integrity on multi-service routes', () => {
  const isolated = [
    'node-component-gateway',
    'node-service-orders',
    'node-service-inventory',
    'node-service-notifications',
    'node-component-rabbitmq',
    'node-component-postgres',
  ];
  const result = computeCompactLayout(isolated);

  const expectedBox = getBoundingBoxForPositions(BASE_NODE_POSITIONS);
  assert.equal(result.boundingBox.width, expectedBox.width);
  assert.equal(result.offsets['node-service-orders'].x, 0);
});

test('computeCompactLayout mobile mode returns mobile bounding box', () => {
  const result = computeCompactLayout(null, true);
  assert.ok(result.boundingBox.width > 0);
  assert.ok(result.boundingBox.height > 0);
  assert.equal(result.offsets['node-service-auth'].x, 0);
});
