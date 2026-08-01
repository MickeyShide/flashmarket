# Storefront and Admin Feature Catch-up Design

**Date:** 2026-08-01  
**Status:** Approved  
**Scope:** Minimal working storefront and admin integration for backend features already added from `ideas.md`

## Goal

Bring the existing React storefront up to date with Drops, Wishlist, product
variants, variant stock, promocodes, and Media. Add a practical admin interface
for managing those features. The result must work end to end while preserving
the current frontend stack and visual style.

The implementation favors the smallest working change. It does not redesign
the storefront, replace its state management, or introduce a frontend
architecture migration.

## Fixed Constraints

- Keep React 18, Vite, Tailwind, JavaScript, Context, and the existing
  `currentView` navigation.
- Do not add React Router, TypeScript, Redux, TanStack Query, form libraries,
  component libraries, SSR, or Next.js.
- Reuse existing UI patterns and Tailwind classes.
- Add no new automated frontend or backend tests as part of this work.
- Verification is limited to existing checks, a production frontend build, and
  a manual end-to-end smoke pass.
- Keep the existing Developer Hub unchanged except for regenerated OpenAPI
  artifacts when backend contracts change.
- Backend authorization remains authoritative. Frontend role checks only hide
  unavailable controls.

## Existing State and Gaps

The storefront currently supports authentication, catalog browsing, a
product-level stock check, a local cart, order creation, mock payment, profile
sessions, notifications, and the Developer Hub.

The following implemented backend features are not integrated into the retail
frontend:

- Drops public discovery and admin lifecycle management;
- Wishlist CRUD;
- product variants and variant-specific inventory;
- promocode validation and discounted order amounts;
- Media uploads and entity-bound assets.

The current contracts also have gaps that prevent a correct UI:

- Wishlist and Drop entries contain product IDs but no efficient product
  hydration contract;
- the cart does not retain `variant_id` and orders do not retain a variant
  snapshot;
- the existing checkout creates one order at a time, so a cart-wide promocode
  cannot be consumed exactly once;
- drop limits and payment timeouts are descriptive fields rather than enforced
  purchase rules;
- `DropStarted` does not create notifications for Wishlist users;
- notification delivery status is incorrectly used by the frontend as read
  status;
- Brand has no update endpoint for storing an uploaded logo.

## Minimal Frontend Structure

The existing `App.jsx` view switch gains these views:

- `drops`;
- `drop-detail`;
- `wishlist`;
- `admin`.

Existing contexts remain. `CartContext` gains variant and drop data, and one
small `WishlistContext` owns the signed-in user's Wishlist IDs and mutations.
Drops and admin pages keep request state locally instead of introducing new
global state.

New feature components live under:

```text
frontend/src/components/
  Drops/
  Wishlist/
  Admin/
  Media/
```

The shared API client remains `frontend/src/services/api.js`. Small domain API
helpers may be added when they prevent duplicating request construction, but no
generated client or new request library is introduced.

## Storefront Design

### Drops

The catalog home shows active and upcoming Drops. Each card contains its cover,
status, start or end time, and a browser countdown. Selecting a Drop opens a
detail view containing its description, limits, payment timeout, and hydrated
product cards.

The browser refreshes the corresponding Drop list when a countdown crosses
zero. No WebSocket integration is added. A product added from a Drop retains
`drop_id` and `drop_slug` in the cart so the server can apply the purchase
policy during reservation.

### Product variants and stock

`ProductDetail` derives selectable sizes and colors from active variants instead
of the hard-coded `S`, `M`, `L`, `XL`, and `OS` array. The selected variant
controls:

- `effective_price`;
- SKU, size, color, material, and color swatch;
- `GET /api/v1/stocks/{product_id}?variant_id=...`;
- the add-to-cart enabled state.

A cart line is identified by `product_id + variant_id`. Lines store a snapshot
of the displayed variant fields. Products without variants retain the existing
product-level stock flow. Old local-storage cart entries without variant fields
remain readable as non-variant lines.

### Wishlist

Signed-in users receive a heart control on product cards and product details.
Visible product IDs are checked in one request. A guest who uses the heart is
sent to the existing authentication view.

The profile gains a Wishlist tab with pagination, hydrated product cards, and a
remove action. The context clears on logout and reloads after login. No anonymous
local Wishlist or merge behavior is introduced.

### Checkout and promocodes

Checkout gains one promocode input. Validation uses the cart amount in minor
currency units. The summary shows original amount, discount, and final amount.

The submit flow is:

1. validate the current cart and optional promocode;
2. reserve every cart line with its variant and optional Drop;
3. call the Orders batch endpoint with all reservation-backed lines;
4. clear the cart after the batch succeeds;
5. show the created orders in the existing profile flow.

If reservation or batch creation fails, the frontend releases every reservation
created during this attempt. The backend revalidates the promocode during order
creation; the preliminary response is display-only.

Order list and detail views display the variant snapshot, original amount,
discount, final amount, promocode, and payment deadline. Mock payment uses the
final discounted amount.

### Media and profile

Product details render the existing cover and ordered image gallery. Drop covers
and brand logos use their stored public URLs.

The profile gains avatar upload and replacement. The shared upload helper:

1. requests a constrained Media upload;
2. submits `FormData` directly to the returned S3/MinIO URL;
3. completes the asset through Media;
4. returns the completed public asset.

The browser validates the declared type and file size before starting. Image
editing, resizing, CDN integration, and private files are excluded.

### Catalog controls

When a search phrase is present, the request uses relevance sorting. The
catalog also exposes the existing price/date sorting and price range parameters.
Public `HIDDEN` and `ARCHIVED` filters are removed. A size filter is backed by a
small Catalog variant filter.

### Notifications and API failures

Notifications use a dedicated read operation and `read_at`; delivery status is
left intact. The unread badge counts records without `read_at`.

The shared API client maps the stable Gateway `429` response to a Russian
retry message and exposes `Retry-After`. It also serializes concurrent token
refresh behind one in-flight promise so parallel API calls do not log out a
valid session.

New screens implement only the essential states: loading, empty, request error,
retry, and disabled submit while a mutation is running.

## Admin Design

An `ADMIN` user receives an Admin entry in the existing header/profile
navigation. `AdminView` contains simple local tabs and is inaccessible to a
non-admin user. It is not a separate application.

### Catalog administration

The Products tab supports paginated listing, search, status filtering, create,
edit, and archive. A new product is created as `HIDDEN`; images, variants, and
stock can then be added before activation.

The product editor includes:

- base product fields;
- cover and ordered gallery upload through Media;
- variant create, update, activation, ordering, and delete;
- variant or product stock create/reset and total update;
- current total, available, reserved, and sold counters.

Categories support tree display and creation with an optional parent. Brands
support creation, editing, and logo upload. Category or Brand deletion is not
added.

### Drop administration

The Drops tab supports:

- paginated status filtering;
- create and edit;
- cover upload;
- product search and item add/remove;
- item ordering;
- schedule, start, end, and cancel transitions.

Only transitions valid for the current status are shown. Lifecycle and delete
actions require confirmation.

### Promocode administration

The Promocodes tab supports listing, creation, and editing of type, value,
currency, minimum amount, maximum discount, global and per-user limits, dates,
and status. Existing usage counts are displayed. Promocodes are disabled rather
than deleted.

Fixed values and order thresholds are entered in rubles and converted to minor
currency units at the API boundary. Percentage values are not converted.

### Media administration

Media upload is embedded in the product, brand, and Drop forms. A small asset
registry lists assets by purpose, entity, uploader, and status, provides a
preview, and supports deletion or retrying a failed upload. Credentials,
presigned fields, and internal storage keys are never rendered.

### Users, audit, and notifications

The existing Auth admin contracts are exposed as a simple user list with role
and active-status changes plus an audit-event list. Dangerous account changes
require confirmation.

A small notification form sends a subject and body to one user and may attach a
completed Media asset. Bulk campaigns and segmentation are excluded.

Admin-wide order management, refunds, shipping, and real payment-provider
operations are excluded because the required backend features do not exist.

## Required Backend Contract Changes

### Catalog

- add public batch product hydration for a bounded list of IDs;
- add optional variant-size filtering to product search;
- add admin Brand update;
- retain product responses with embedded variants.

### Inventory

- persist optional `drop_id` on a reservation;
- accept `variant_id` and `drop_id` during reserve;
- for Drop reservations, fetch the current public Drop policy and fail closed if
  it cannot be verified;
- verify ACTIVE status, product membership, and `max_per_user` using the user's
  reservations for the Drop;
- derive reservation expiry from `payment_timeout_seconds`;
- run a small expiry worker that releases overdue reservations.

Non-Drop reservations keep their existing behavior.

### Orders

- add nullable variant snapshot fields to orders;
- add a bounded batch-create request and response;
- lock and validate one optional promocode against the aggregate amount;
- distribute the discount across lines with deterministic minor-unit rounding;
- create all orders, usage, and outbox records in one database transaction;
- expose checkout totals and per-order original, discount, and final amounts.

### Wishlist and Notifications

- consume `DropStarted` and resolve matching Wishlist users without duplicate
  notifications;
- add nullable `read_at` to notifications;
- add an owner/admin read operation;
- keep delivery transitions separate from read state.

### Media and Brand binding

No Media storage contract changes are required. The Brand update endpoint and
existing Product/Drop update endpoints persist the completed `public_url`.
User avatars are discovered through the existing `user` entity binding, so Auth
does not need a new avatar field.

## Error and Recovery Rules

- Drop-policy verification failure rejects a Drop reservation; it does not fall
  back to an unrestricted purchase.
- A failed cart reservation releases the reservations already created in that
  browser attempt.
- A failed Orders batch produces no partial Orders database state.
- An upload is not attached until Media completion succeeds.
- A failed replacement upload leaves the previous image or avatar untouched.
- `401` performs the existing single refresh attempt; `403` never refreshes.
- Duplicate Wishlist and promocode conflicts are shown as normal form/action
  errors rather than fatal pages.
- Existing server-side ownership and role failures remain visible as access
  errors.

## Implementation Order

1. Add the minimal Catalog, Inventory, Orders, Wishlist, Notifications, and
   Brand contracts and migrations.
2. Regenerate the Developer Hub OpenAPI artifacts.
3. Extend the shared frontend API behavior and cart data shape.
4. Implement variants and variant stock in product, cart, checkout, and orders.
5. Implement Wishlist controls and profile tab.
6. Implement public Drop discovery, details, countdowns, and Drop checkout data.
7. Implement promocode validation and batch checkout.
8. Implement the shared Media upload helper and profile avatar.
9. Implement Admin shell, Catalog, variants, stock, categories, and brands.
10. Implement Admin Drops and promocodes.
11. Implement Admin Media, users, audit, and individual notifications.
12. Run existing checks, build the frontend, and manually smoke the complete
    customer/admin flow.

## Verification

No new automated test suites or test dependencies are added.

The implementation is considered verified when:

- existing repository checks affected by contract changes still run;
- `npm run build` completes;
- Docker Compose configuration renders;
- a manual smoke pass completes this flow:
  - admin creates a hidden product, variant, image, and stock;
  - admin creates and schedules a Drop containing that product;
  - customer adds it to Wishlist;
  - Drop starts and the customer receives a notification;
  - customer selects the stocked variant and adds it from the Drop;
  - customer applies a promocode and creates the checkout;
  - the displayed and paid amount matches the discounted total;
  - admin can inspect the resulting usage and current managed entities.

## Out of Scope

- frontend redesign or design-system work;
- frontend framework, routing, state-management, or language migration;
- new automated tests or browser-test infrastructure;
- SSR, SSG, PWA, WebSockets, Storybook, analytics, or frontend observability;
- real payment providers;
- delivery integrations, reviews, loyalty, internationalization, or push
  notifications;
- bulk marketing tools;
- refunds, returns, or full order-management back office;
- image resizing, cropping, optimization, private media, or CDN provisioning.

## Acceptance Criteria

- Customer and Admin can use every feature listed in this design through the
  existing frontend application.
- Variant selection controls the displayed price, stock request, cart identity,
  reservation, order snapshot, and order display.
- Drop membership, lifecycle, user limit, and payment timeout are enforced by
  the backend.
- Wishlist state persists across sessions and produces one notification per
  applicable Drop/user event.
- One promocode applies once to the aggregate checkout and all displayed/payment
  totals agree.
- Product, Brand, Drop, and avatar uploads complete through Media and render via
  their public URLs.
- Non-admin users cannot execute administrative operations.
- Existing non-variant and non-Drop products continue through the old purchase
  flow.
- The production frontend build succeeds and the agreed manual smoke flow works.
