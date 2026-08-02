# Lazy Loading and Page Performance Design

## Goal

Reduce initial page load time, network transfer, image decoding work, and unnecessary React rendering without changing the site's visual design. The storefront catalog and long administration lists must automatically fetch the next page as the user approaches the end of the currently loaded content.

## Scope

This change covers:

- automatic incremental loading for the storefront product catalog;
- automatic incremental loading for administration products, drops, promocodes, media assets, users, and audit events;
- route-level code splitting for secondary storefront views;
- tab-level code splitting inside the administration panel;
- native lazy loading and asynchronous decoding for non-critical images;
- request deduplication, stale-response protection, retry behavior, and pagination tests.

Brands and categories remain fully loaded because they are small navigation dictionaries and their current APIs do not expose paginated workflows. Drop product selectors may continue to load their bounded product lookup independently from the paginated drop list because an editor needs the complete lookup while the form is open.

Profile orders, notifications, wishlist items, and the full public drops listing are follow-up candidates. They are not part of this implementation so the first delivery remains focused and independently verifiable.

## Chosen Approach

Use server-backed pagination with an `IntersectionObserver` sentinel. Each list fetches a small first page and appends the next page when the sentinel approaches the viewport. Existing manual loading controls remain available as a fallback, so keyboard users, browsers without `IntersectionObserver`, and failed automatic requests retain an explicit action.

This is preferred over client-only incremental rendering because client-only rendering still downloads the full data set up front. Full list virtualization is not justified at the current data volume and could change scroll behavior, element measurement, and table semantics.

## Shared Infinite-Scroll Primitive

A small reusable hook owns viewport observation only. Its public inputs are:

- whether more data exists;
- whether a request is already running;
- the callback that requests the next page;
- an optional prefetch margin.

It returns a ref for a stable sentinel element. The observer is disabled while loading or when no further page exists. The default root margin should start loading before the sentinel is visibly reached, avoiding a pause at the bottom of the list. If `IntersectionObserver` is unavailable, no automatic request is attempted and the existing button remains functional.

Pagination state and API-specific response handling stay inside each page component. This keeps the shared primitive independent of endpoint shape, filters, and mutation behavior.

## Storefront Catalog

The catalog retains its existing page size of 20 and `limit`/`offset` API contract. Initial loads replace the list; subsequent loads append unique products. The bottom loading control contains the observation sentinel and preserves the current button markup and styling.

Changing category, brand, size, price, sort order, or search query starts a new pagination generation at offset zero. Responses from an older generation must not replace or append to the new result set. Repeated observer events while a request is active must not issue duplicate requests.

The total returned by the API is authoritative. `hasMore` is true only while the number of loaded records is below the total and the last request produced records.

## Administration Lists

The following tabs switch from a single `limit=100` request to server-backed pages:

- products;
- drops;
- promocodes;
- media assets;
- users;
- audit events.

Each tab keeps its existing mobile cards, desktop table, controls, forms, and styling. Both responsive renderings use the same paginated data state and one sentinel after the list, so only one next-page request can run.

Products require special handling because the public product endpoint defaults to `ACTIVE` when no status is supplied. The administration tab therefore continues to request explicit statuses. For the `ALL` filter, it maintains bounded requests for `ACTIVE`, `HIDDEN`, and `ARCHIVED` and combines unique results; for a selected status, only that status is fetched. The search phrase is sent to the API rather than applied only to the loaded subset. Changing status or search resets pagination.

Drops send the selected status to the API when a status filter is active. Promocodes, media assets, users, and audit events use the `total`, `limit`, and `offset` fields already exposed by their APIs. Filters supported by an endpoint are sent with every page request. A filter that is strictly presentational may continue to act on the loaded set only if the API has no equivalent parameter, and its label must not imply a global search.

After a successful create, update, archive, delete, role change, or status change, the affected tab refreshes from its first page. This avoids gaps and duplicates caused by data moving between pages. Forms keep their current local state and are not closed solely because another page is appended.

## Code Splitting

Secondary storefront views are loaded with `React.lazy` and `Suspense`, including product detail, cart, checkout, profile, order detail, categories, public drops, drop detail, and administration. The existing developer hub remains lazy-loaded.

Administration tabs are also lazy imports. Opening the panel downloads the administration shell and default products tab; other tab chunks load only when selected. Suspense fallbacks reuse the current spinner or an inert size-preserving container and introduce no new visual treatment.

Small layout components, the header, navigation, catalog controls, and the first catalog view remain in the initial bundle because they are required immediately.

## Image Loading

Non-critical `<img>` elements receive `loading="lazy"` and `decoding="async"`. This includes product cards below the initial viewport, administration thumbnails, media previews, gallery thumbnails, category/brand content outside the first viewport, and profile content that is not initially rendered.

The first visible row of storefront product cards remains eager and may use high fetch priority so the largest above-the-fold image is not delayed. Product detail's selected primary image also remains eager; only its thumbnails are lazy. Width, height, or existing aspect-ratio containers continue to reserve layout space, preventing layout shifts.

CSS background images cannot use native `loading="lazy"`. Existing background-based cards remain unchanged unless they are converted to an absolutely positioned `<img>` with identical sizing, crop, overlay, border radius, and stacking. Such a conversion is allowed only when visual parity can be verified.

## Concurrency and Error Handling

Every paginated loader enforces these rules:

1. Do not start a next-page request while an initial or next-page request is active.
2. Ignore responses belonging to an obsolete filter/search generation.
3. Append by stable entity ID and discard duplicates.
4. Preserve already loaded records when a later page fails.
5. Expose the existing loading state and a retry action for the failed page.
6. Stop observing once all records are loaded or an empty page is returned.

Where practical, obsolete fetches should be aborted. Generation checks remain required because an abort may race with response completion.

## Accessibility and User Experience

Automatic loading must not remove keyboard access to manual loading. The existing button remains reachable and labeled. The loading state prevents double activation and uses `aria-busy` on the list region or loading control. Appended records keep natural DOM order; focus is never moved after an automatic load.

No colors, spacing, typography, card dimensions, table structure, transitions, or navigation behavior are intentionally changed. Loading starts before the user reaches the end so the common path feels continuous without introducing a new skeleton design.

## Testing and Verification

Unit tests cover the shared observer behavior:

- it requests the next page when the sentinel intersects;
- it does not request while loading;
- it does not request when `hasMore` is false;
- repeated observer callbacks do not cause parallel duplicate requests;
- absence of `IntersectionObserver` leaves manual loading operational.

Page-level tests cover:

- replacing the catalog after a filter change;
- ignoring stale responses;
- appending unique records and stopping at `total`;
- resetting administration pagination after mutations;
- product status and search query construction;
- retrying a failed later page without discarding prior records.

Verification also includes the existing frontend test suite and a production Vite build. Build output is inspected to confirm that secondary routes and administration tabs are emitted as separate chunks. A manual responsive smoke test checks the storefront and each affected administration tab at mobile and desktop widths, including scrolling, filtering, form editing, failed requests, and the manual fallback button.

## Success Criteria

- The first catalog request transfers at most 20 products.
- Each affected administration list transfers one bounded page rather than 100 records on entry.
- Approaching the bottom automatically loads the next page exactly once.
- Filter changes and mutations cannot append stale or duplicate records.
- Secondary pages and inactive administration tabs are absent from the initial JavaScript chunk.
- Below-the-fold images do not begin loading eagerly in supporting browsers.
- Existing visuals and interaction controls remain unchanged.
- Existing tests, new pagination tests, and the production frontend build pass.
