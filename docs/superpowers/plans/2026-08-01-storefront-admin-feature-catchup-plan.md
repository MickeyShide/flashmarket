# Storefront and Admin Feature Catch-up Implementation Plan

**Design:** `docs/superpowers/specs/2026-08-01-storefront-admin-feature-catchup-design.md`  
**Approach:** smallest working changes, existing frontend architecture, no new tests

## Working Rules

- Preserve React, Vite, Tailwind, JavaScript, Context, and `currentView`.
- Do not add frontend dependencies.
- Do not redesign existing screens.
- Do not add automated tests or test infrastructure.
- Preserve the user's current uncommitted `docker-compose.yml` changes. Inspect
  its diff before editing and patch only the required service blocks.
- Keep existing public APIs backward compatible where possible.
- After backend route changes, regenerate the checked-in Developer Hub OpenAPI
  artifacts.

## Phase 1 — Catalog contracts needed by both frontends

### Task 1. Add bounded product hydration

Files:

- `catalog/src/catalog/application/schemas.py`
- `catalog/src/catalog/application/contracts.py`
- `catalog/src/catalog/application/services/product.py`
- `catalog/src/catalog/infrastructure/repositories/product.py`
- `catalog/src/catalog/api/routes/products.py`

Changes:

1. Add a batch request containing 1–100 unique product UUIDs.
2. Add `POST /api/v1/products/batch` before the dynamic `/{slug}` route.
3. Load products with the same category, brand, images, and variants relations
   as normal product responses.
4. Return only public ACTIVE products to anonymous callers.
5. Preserve request order in the response so Drop item ordering remains stable.
6. Keep missing or hidden IDs absent instead of failing the whole batch.

Done when Wishlist and Drops can hydrate up to 100 product IDs in one request.

### Task 2. Add size filtering and Brand editing

Files:

- `catalog/src/catalog/application/schemas.py`
- `catalog/src/catalog/infrastructure/repositories/product.py`
- `catalog/src/catalog/api/routes/brands.py`
- `catalog/src/catalog/application/services/brand.py`

Changes:

1. Add optional `size` to `ProductListParams`.
2. Filter products through active variants and keep product pagination distinct.
3. Add `PATCH /api/v1/brands/{brand_id}` using the existing
   `UpdateBrandRequest` fields.
4. Allow the Brand patch to persist the completed Media `logo_url`.

Done when the storefront can filter by available variant size and Admin can
attach or replace a Brand logo.

## Phase 2 — Enforce Drop purchase rules in Inventory

### Task 3. Add a stable Drop lookup by ID

Files:

- `drops/src/drops/api/routes/drops.py`
- `drops/src/drops/application/services/drop.py`

Changes:

1. Add `GET /api/v1/drops/id/{drop_id}` before `/{slug}`.
2. Return the normal public Drop response.
3. Hide DRAFT and CANCELLED Drops using the existing public visibility rule.

Done when Inventory can resolve the authoritative Drop policy using `drop_id`.

### Task 4. Persist Drop data on reservations

Files:

- new Inventory Alembic migration
- `inventory/src/inventory/infrastructure/models.py`
- `inventory/src/inventory/application/schemas.py`
- `inventory/src/inventory/infrastructure/repositories/stock.py`
- `inventory/src/inventory/application/services/stock.py`
- `inventory/src/inventory/api/routes/stock.py`

Changes:

1. Add nullable `drop_id` to reservations and include it in responses.
2. Accept `drop_id` alongside the existing `variant_id` in `ReserveRequest`.
3. Add repository counting for ACTIVE and COMMITTED quantities belonging to
   one `user_id + drop_id`.
4. Before counting, treat already expired ACTIVE reservations as expired.
5. Serialize concurrent limit checks for the same user and Drop with a
   PostgreSQL transaction advisory lock.
6. Keep non-Drop reservations unchanged.

Done when variant and Drop identity survive the complete reservation lifecycle.

### Task 5. Resolve and enforce Drop policy

Files:

- `inventory/src/inventory/config.py`
- new `inventory/src/inventory/infrastructure/drop_client.py`
- `inventory/src/inventory/api/dependencies.py`
- `inventory/src/inventory/application/services/stock.py`
- Inventory Compose environment files

Changes:

1. Add internal Drops base URL and a short HTTP timeout.
2. For a Drop reservation, load the current Drop by ID.
3. Verify status is ACTIVE and `product_id` belongs to its items.
4. Reject a quantity that would exceed `max_per_user` across variants.
5. Set `expires_at` using the Drop's `payment_timeout_seconds`.
6. Fail closed with a service-unavailable response when the Drop policy cannot
   be verified.
7. Use the existing default reservation TTL for non-Drop purchases.

Done when changing browser payloads cannot bypass Drop membership, limit, or
payment timeout.

### Task 6. Run reservation expiry continuously

Files:

- new `inventory/src/inventory/expiry_worker.py`
- `inventory/docker-compose.yml`
- `inventory/docker-compose.deploy.yml`
- root `docker-compose.yml`
- `docker-compose.prod.yml` if Inventory workers are declared there

Changes:

1. Reuse the existing `expire_reservations()` application behavior.
2. Run it in a small loop with configurable interval and graceful shutdown.
3. Add an `inventory-expiry` service using the existing Inventory image.
4. Preserve all unrelated local edits in root Compose.

Done when expired Drop reservations release stock without an HTTP caller.

## Phase 3 — Batch checkout and correct order totals

### Task 7. Store variant and checkout snapshots

Files:

- new Orders Alembic migration
- `orders/src/orders/infrastructure/models.py`
- `orders/src/orders/application/schemas.py`
- `orders/src/orders/domain/entities.py` if shared DTOs are defined there

Changes:

1. Add nullable `checkout_id`, `variant_id`, `variant_sku`, `variant_size`,
   `variant_color`, `drop_id`, and `payment_expires_at` to Order.
2. Keep `price` as the original per-unit amount.
3. Keep `original_price`, `discount_amount`, and `final_price` as line totals in
   minor currency units.
4. Return all new fields from single-order and list responses.
5. Preserve existing single-order creation for backward compatibility.

Done when an order remains understandable even if its Catalog variant later
changes or is deleted.

### Task 8. Add transactional batch order creation

Files:

- `orders/src/orders/application/schemas.py`
- `orders/src/orders/application/services/order.py`
- `orders/src/orders/application/services/promocode.py`
- `orders/src/orders/infrastructure/repositories/order.py`
- `orders/src/orders/api/routes/orders.py`

Changes:

1. Add `POST /api/v1/orders/batch` for 1–100 reservation-backed lines.
2. Require every line to belong to the authenticated user unless the caller is
   ADMIN.
3. Reject duplicate reservation IDs in one request.
4. Calculate the aggregate original amount.
5. Lock and validate the optional promocode once against that aggregate.
6. Allocate the minor-unit discount proportionally across lines; give rounding
   remainder deterministically to lines with the largest fractional remainder.
7. Create every Order and outbox event without intermediate commits.
8. Record one promocode usage linked to the first order in the checkout.
9. Commit once and return orders plus aggregate original, discount, and final
   amounts.
10. Roll back the complete Orders transaction on any failure.

Done when one cart submission creates all line orders and consumes its promo
exactly once.

### Task 9. Use final totals throughout payment flow

Files:

- `orders/src/orders/application/services/order.py`
- `orders/src/orders/outbox_worker.py` if it transforms payment events
- `payments/src/payments/event_consumer.py`
- related payment schemas only if the event contract requires it

Changes:

1. Publish each order's `final_price` as its payment amount.
2. Stop deriving payment amounts from discounted per-unit integer division.
3. Keep existing non-discounted orders producing the same amount as before.

Done when Orders, Payments, and frontend show the same payable amount.

## Phase 4 — Wishlist Drop alerts and notification read state

### Task 10. Produce targeted Wishlist events on Drop start

Files:

- `wishlist/pyproject.toml` and lock file
- `wishlist/src/wishlist/config.py`
- `wishlist/src/wishlist/infrastructure/repositories/wishlist.py`
- new `wishlist/src/wishlist/event_consumer.py`
- `wishlist/docker-compose.yml`
- root `docker-compose.yml`

Changes:

1. Add the existing project RabbitMQ client dependency to Wishlist.
2. Listen for `drops.DropStarted`.
3. Query distinct users whose Wishlist contains any event `product_ids`.
4. Publish one `wishlist.DropAvailable` event per matching user containing a
   stable event key, Drop ID, slug, and name.
5. Acknowledge the Drop event only after targeted events are published.
6. Add a `wishlist-consumer` process to Compose while preserving unrelated
   user edits.

Done when a Drop start is converted into one targeted event per interested
user.

### Task 11. Separate delivery and read state

Files:

- new Notifications Alembic migration
- `notifications/src/notifications/infrastructure/models.py`
- `notifications/src/notifications/application/schemas.py`
- `notifications/src/notifications/infrastructure/repositories/notification.py`
- `notifications/src/notifications/api/routes/notifications.py`
- `notifications/src/notifications/event_consumer.py`

Changes:

1. Add nullable `read_at`, nullable unique `event_key`, and optional
   `attachment_url` to notifications.
2. Include these fields in API responses.
3. Add owner/admin `POST /api/v1/notifications/{id}/read`.
4. Add `wishlist.DropAvailable` handling.
5. Deduplicate Drop notifications by `event_key`.
6. Leave `send` and `fail` as delivery-state operations.
7. Allow the existing Admin create endpoint to accept an optional completed
   attachment URL.

Done when the bell has a real unread state and Drop alerts cannot duplicate.

## Phase 5 — Shared minimal frontend plumbing

### Task 12. Harden the existing API helper only where needed

Files:

- `frontend/src/services/api.js`
- optional new `frontend/src/services/media.js`

Changes:

1. Replace the boolean refresh flag with one shared in-flight refresh promise.
2. Retry all waiting authenticated requests once after a successful refresh.
3. Preserve current logout behavior after refresh failure.
4. Map `429` to a short Russian message and expose parsed `Retry-After` on the
   thrown error.
5. Add a Media upload helper for create → direct FormData POST → complete.
6. Do not route the direct S3 upload through `apiJson` or attach JWT/CSRF headers
   to it.

Done when parallel feature requests share refresh correctly and Media files can
complete.

### Task 13. Extend Cart without replacing it

Files:

- `frontend/src/context/CartContext.jsx`
- `frontend/src/components/Cart/CartView.jsx`

Changes:

1. Store variant snapshot and optional Drop fields on each line.
2. Use product plus variant as the line key.
3. Request stock using the line's optional `variant_id`.
4. Preserve and read old local-storage entries without migration prompts.
5. Display SKU, size, color, and Drop label only when present.

Done when two variants of one product remain separate and quantity checks hit
the correct stock row.

### Task 14. Add signed-in Wishlist state

Files:

- new `frontend/src/context/WishlistContext.jsx`
- `frontend/src/main.jsx`
- `frontend/src/context/AuthContext.jsx` only for login/logout coordination if
  required

Changes:

1. Store a Set-compatible list of wished product IDs.
2. Provide batch check, add, remove, list, and clear operations.
3. Load after a user becomes available and clear on logout.
4. Use existing Toast feedback and avoid optimistic state if a request has not
   succeeded.

Done when all visible Wishlist controls reflect server state.

## Phase 6 — Customer-facing screens

### Task 15. Replace hard-coded variant UI

Files:

- `frontend/src/components/Product/ProductDetail.jsx`
- `frontend/src/components/Catalog/ProductCard.jsx`
- `frontend/src/components/Catalog/CatalogControls.jsx`
- `frontend/src/App.jsx`

Changes:

1. Build size/color controls from active variants.
2. Select the first valid in-stock option when practical.
3. Request stock whenever the chosen variant changes.
4. Display `effective_price` and variant metadata.
5. Pass the complete selected line to Cart.
6. Add size, price, and sort controls to the existing compact catalog toolbar.
7. Use `sort_by=relevance` while search is non-empty.
8. Remove public HIDDEN/ARCHIVED status controls.
9. Add heart buttons using Wishlist context.

Done when Catalog → Product → Cart works for variant and non-variant products.

### Task 16. Add Wishlist profile tab

Files:

- new `frontend/src/components/Wishlist/WishlistView.jsx`
- `frontend/src/components/Profile/ProfileView.jsx`
- `frontend/src/components/Layout/Header.jsx`
- `frontend/src/components/Layout/CategoryNav.jsx`
- `frontend/src/App.jsx`

Changes:

1. Add the profile tab and optional header count.
2. Load paged Wishlist items.
3. Hydrate product IDs through Catalog batch.
4. Reuse ProductCard and existing empty/loading/error patterns.
5. Remove an item through the existing Wishlist endpoint.
6. Send guests using a heart to the Auth view.

Done when a signed-in user can add, browse, open, and remove wished products.

### Task 17. Add public Drops views

Files:

- new `frontend/src/components/Drops/DropCard.jsx`
- new `frontend/src/components/Drops/DropsSection.jsx`
- new `frontend/src/components/Drops/DropDetail.jsx`
- new `frontend/src/components/Drops/Countdown.jsx`
- `frontend/src/App.jsx`
- `frontend/src/components/Layout/CategoryNav.jsx`

Changes:

1. Load active and upcoming Drops on the catalog home.
2. Render compact cards with the existing storefront style.
3. Add a Drops navigation entry and `drop-detail` view.
4. Hydrate and order Drop products through Catalog batch.
5. Refresh the relevant data when a countdown reaches zero.
6. Pass Drop identity into ProductDetail and then Cart.
7. Show max quantity and payment timeout without adding real-time transport.

Done when users can discover a Drop and carry its product policy into checkout.

### Task 18. Add promocode batch checkout

Files:

- `frontend/src/components/Checkout/CheckoutView.jsx`
- `frontend/src/context/CartContext.jsx`
- `frontend/src/components/Profile/OrdersTab.jsx`
- `frontend/src/components/Order/OrderDetailView.jsx`
- `frontend/src/utils/formatters.js`

Changes:

1. Add apply/remove promocode controls.
2. Convert cart ruble totals to minor units for Orders validation.
3. Display original, discount, and final totals.
4. Reserve every line with variant and Drop IDs while recording rollback data.
5. Submit one Orders batch after all reservations succeed.
6. Release recorded reservations if batch creation fails.
7. Clear Cart and open Orders after success.
8. Display variant, promo, original, discount, final, and deadline in Orders.
9. Create/confirm mock payments using `final_price`.
10. Disable submit and payment controls while their request is active.

Done when a multi-line cart uses one promocode and displayed/payment totals
match the backend response.

### Task 19. Add avatar and correct notification reads

Files:

- `frontend/src/components/Profile/ProfileView.jsx`
- `frontend/src/context/AuthContext.jsx`
- `frontend/src/components/Profile/NotificationsTab.jsx`
- `frontend/src/components/Layout/Header.jsx`

Changes:

1. Load the newest completed `user_avatar` asset for the signed-in user.
2. Add image selection, client type/size validation, upload, and replacement.
3. Keep the old avatar until the new upload completes.
4. Use `/read` when a notification is opened.
5. Count unread items by missing `read_at`.
6. Render Drop notification text and optional attachment link.

Done when profile avatar and notification unread behavior are persistent.

## Phase 7 — Minimal Admin application

### Task 20. Add Admin shell and access gate

Files:

- new `frontend/src/components/Admin/AdminView.jsx`
- new `frontend/src/components/Admin/AdminNav.jsx`
- `frontend/src/App.jsx`
- `frontend/src/components/Layout/Header.jsx`

Changes:

1. Add `currentView='admin'`.
2. Show entry only for ADMIN.
3. Redirect or render access denied if a non-admin reaches the view.
4. Add local tabs without Router.
5. Reuse plain loading/error blocks and Toast.

Done when Admin has a protected, usable container with no new dependency.

### Task 21. Implement Catalog, variants, stock, categories, and brands

Files:

- new files under `frontend/src/components/Admin/Catalog/`
- new files under `frontend/src/components/Admin/Inventory/`
- shared Media uploader component under `frontend/src/components/Media/`

Changes:

1. Product list with existing server pagination and filters.
2. Create and edit form using plain controlled inputs.
3. Archive confirmation.
4. Product creation defaults to HIDDEN.
5. Upload cover/gallery only after the product has an ID, then patch URLs.
6. Variant list and create/edit/delete forms.
7. Product or variant stock read, create/reset, and total update.
8. Category tree and create form.
9. Brand list, create/edit form, and logo upload.
10. Keep each form on one screen; do not build a generic form framework.

Done when Admin can prepare a complete stocked product and activate it.

### Task 22. Implement Drop management

Files:

- new files under `frontend/src/components/Admin/Drops/`

Changes:

1. List and filter by lifecycle status.
2. Create/edit fields and cover upload.
3. Search Catalog products and add/remove Drop items.
4. Edit item ordering using numeric order inputs rather than drag-and-drop.
5. Show only valid lifecycle transition buttons.
6. Confirm schedule/start/end/cancel operations.
7. Reload the current Drop after every successful mutation.

Done when Admin can create the Drop used by the customer smoke flow.

### Task 23. Implement promocode management

Files:

- new files under `frontend/src/components/Admin/Promocodes/`

Changes:

1. Paginated list with status and current usage.
2. Create/edit form for every existing backend field.
3. Convert fixed amounts, thresholds, and caps between rubles and minor units.
4. Keep percentage values unchanged.
5. Disable via status instead of providing delete.

Done when Admin can create and later inspect the promo used at checkout.

### Task 24. Implement Media, users, audit, and notifications

Files:

- new files under `frontend/src/components/Admin/Media/`
- new files under `frontend/src/components/Admin/Users/`
- new files under `frontend/src/components/Admin/Audit/`
- new files under `frontend/src/components/Admin/Notifications/`

Changes:

1. Media asset list with query filters, preview, status, and delete.
2. User list with role and active-state changes plus confirmation.
3. Audit-event paginated list.
4. Individual notification form with subject, body, channel, and optional Media
   attachment.
5. Keep these as simple tables/forms; no dashboard charts or bulk actions.

Done when all agreed lightweight Admin tabs execute their real APIs.

## Phase 8 — Contract artifacts and runnable verification

### Task 25. Regenerate generated API artifacts

Files:

- `frontend/public/dev/openapi.json`
- `frontend/public/dev/services.json`

Changes:

1. Run the repository OpenAPI generator after all backend routes stabilize.
2. Confirm new public/auth/admin operations have correct access metadata.
3. Do not hand-edit generated JSON.

Done when Developer Hub exposes the current contracts.

### Task 26. Build and manually smoke the feature set

Commands/checks:

1. Render Docker Compose configuration without changing unrelated settings.
2. Build the frontend with `npm run build`.
3. Start the required stack using the existing local workflow.
4. Complete this manual flow:
   - Admin creates Brand/Category if needed.
   - Admin creates hidden Product, uploads images, adds Variant and stock.
   - Admin activates the Product.
   - Admin creates Promocode.
   - Admin creates and starts a Drop containing the Product.
   - Customer adds the Product to Wishlist before Drop start.
   - Customer receives and reads the Drop notification.
   - Customer selects the stocked Variant and adds it from the Drop.
   - Customer applies the Promocode and completes batch checkout.
   - Customer pays the final discounted mock amount.
   - Admin sees current promo usage and managed entity state.
5. Fix only failures found in this agreed flow; do not expand into unrelated
   frontend cleanup.

Done when the production build succeeds and the complete customer/Admin flow
works using real local services.

## Delivery Order Summary

1. Catalog hydration/filter/Brand contracts.
2. Drop policy lookup and Inventory enforcement.
3. Orders batch checkout and correct payment amounts.
4. Wishlist Drop events and notification read state.
5. Shared API, Cart, Wishlist, and Media frontend plumbing.
6. Customer variants, Wishlist, Drops, checkout, orders, avatar, notifications.
7. Admin Catalog/Inventory, Drops, Promocodes, Media, Users, Audit, Notifications.
8. OpenAPI regeneration, build, and manual smoke.

Do not begin a later phase while a contract needed by that phase remains
undefined or returns placeholder data.
