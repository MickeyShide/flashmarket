# FlashMarket Architecture Explorer

The explorer is a dependency-free static page. It uses native ES modules, so run it through a minimal local HTTP server from the repository root:

```powershell
python -m http.server 4173
```

Then open:

```text
http://localhost:4173/docs/architecture/
```

No build step or package installation is required. Architecture content comes from `architecture-data.js`; the page does not call or mutate FlashMarket services.

## Verification

```powershell
node --test docs/architecture/architecture-page.test.mjs
```

In the browser, verify the map filters and service drawer, move through a flow, select an event, run both Outbox simulations, switch Presentation/Deep Dive, and open search with `Ctrl+K` or `Cmd+K`.
