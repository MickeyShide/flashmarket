import assert from 'node:assert/strict';
import test from 'node:test';

import { uploadPresignedFile } from '../src/services/media-upload.js';

function testFile() {
  return new File(['image-bytes'], 'picture.png', { type: 'image/png' });
}

test('presigned upload sends all signed fields and the file without extra headers', async () => {
  const originalFetch = globalThis.fetch;
  let request;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return new Response(null, { status: 204 });
  };

  try {
    await uploadPresignedFile(testFile(), 'http://localhost:9000/flashmarket-public', {
      key: 'product/asset/picture.png',
      policy: 'signed-policy'
    });
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(request.url, 'http://localhost:9000/flashmarket-public');
  assert.equal(request.options.method, 'POST');
  assert.equal(request.options.headers, undefined);
  assert.equal(request.options.body.get('key'), 'product/asset/picture.png');
  assert.equal(request.options.body.get('policy'), 'signed-policy');
  assert.equal(request.options.body.get('file').name, 'picture.png');
});

test('presigned upload turns a network or CORS failure into an actionable error', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError('Failed to fetch');
  };

  try {
    await assert.rejects(
      uploadPresignedFile(testFile(), 'http://localhost:9000/flashmarket-public'),
      /Хранилище файлов недоступно.*CORS/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('presigned upload reports storage HTTP failures and rejects a missing URL', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(null, { status: 403 });

  try {
    await assert.rejects(
      uploadPresignedFile(testFile(), 'http://localhost:9000/flashmarket-public'),
      /сервер хранения: 403/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }

  await assert.rejects(uploadPresignedFile(testFile(), ''), /не вернул адрес/);
});
