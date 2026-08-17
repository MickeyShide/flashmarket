import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

test('Vite dev server routes /architecture and /docs/architecture to React SPA', async () => {
  const server = await createServer({
    configFile: './vite.config.js',
    server: { port: 3099 },
  });
  await server.listen();

  try {
    const address = server.httpServer.address();
    const host = typeof address === 'string' ? address : `http://localhost:${address.port}`;

    const res = await fetch(`${host}/architecture`, {
      headers: { Accept: 'text/html' }
    });
    const html = await res.text();
    assert.equal(res.status, 200);
    assert.ok(html.includes('id="root"'), 'Should serve the React SPA root HTML');

    const docsRes = await fetch(`${host}/docs/architecture`, {
      headers: { Accept: 'text/html' }
    });
    const docsHtml = await docsRes.text();
    assert.equal(docsRes.status, 200);
    assert.ok(docsHtml.includes('id="root"'), 'Should serve the React SPA root HTML for /docs/architecture');
  } finally {
    await server.close();
  }
});
