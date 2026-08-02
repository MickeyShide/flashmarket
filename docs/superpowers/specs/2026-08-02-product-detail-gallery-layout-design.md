# Product Detail Gallery Layout

## Context

The Product detail page currently places the main image, thumbnails, and product
information as three independent children of a two-column CSS Grid. On desktop the
thumbnail list starts a second grid row in the left column, so auto-placement puts the
product information into that second row on the right. The information therefore
starts below the main image and the page appears vertically displaced.

The cover image is displayed as the initial main image but is not included in the
thumbnail list, which prevents returning to it after another gallery image is selected.

## Goals

- Keep the gallery and all of its thumbnails in one left-column grid cell.
- Start product information at the top of the right column on desktop.
- Preserve the mobile order: gallery, thumbnails, then product information.
- Include `cover_image` as the first thumbnail.
- Deduplicate the cover when the same URL is also present in `images`.
- Preserve image selection, variant selection, stock, wishlist, and cart behavior.

## Design

Product images are normalized into one memoized gallery array. The cover becomes the
first item when present, followed by `images` sorted by `sort_order`. Entries with an
empty URL are ignored and duplicate URLs are removed while preserving the first
occurrence. Gallery entries keep the existing media identifier where available and use
a URL-derived fallback key.

The main image and thumbnail row are wrapped in one left-column container. Thumbnails
appear directly below the fixed-height main image with consistent spacing and wrapping.
The selected thumbnail keeps the existing dark border; the cover thumbnail receives an
accessible label identifying it as the product cover.

The product information remains the second direct grid child. It is top-aligned instead
of vertically centered, so its brand, title, and price begin level with the main image.
The grid remains one column below the existing `md` breakpoint and two columns above it.

## Edge Cases

- No cover and no gallery images: retain the existing branded placeholder and render no
  thumbnail row.
- Cover only: render one selected thumbnail.
- Cover duplicated in `images`: render it once, first.
- Broken or unusually tall source image: the existing fixed-height, cover-cropped main
  viewport prevents the source aspect ratio from changing page geometry.
- Product change: selection resets to the first normalized gallery item as it does now.

## Verification

- A desktop contract test confirms that the gallery is one grid child and product info
  is the other top-aligned child.
- Gallery normalization tests cover cover-first ordering, sorting, missing URLs, and
  duplicate removal.
- The frontend test suite and production build pass.
- Manual desktop verification confirms both columns begin at the same height.
- Manual narrow-viewport verification confirms gallery, thumbnails, and information do
  not overlap or reorder incorrectly.

## Acceptance Criteria

- The information panel no longer drops beneath the thumbnail row.
- The cover is visible and selectable in the thumbnail list.
- Each distinct media URL appears exactly once in the thumbnails.
- Desktop and mobile layouts retain their intended widths without horizontal overflow.
