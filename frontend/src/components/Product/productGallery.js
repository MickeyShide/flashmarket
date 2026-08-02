export function buildProductGallery(coverImage, images = []) {
  const gallery = [];
  const seenUrls = new Set();

  const addImage = (image, isCover = false) => {
    const source = typeof image === 'string' ? { url: image } : image;
    const url = source?.url?.trim();

    if (!url || seenUrls.has(url)) return;

    seenUrls.add(url);
    gallery.push({
      ...source,
      url,
      isCover
    });
  };

  addImage(coverImage, true);

  [...(Array.isArray(images) ? images : [])]
    .sort((a, b) => (a?.sort_order || 0) - (b?.sort_order || 0))
    .forEach(image => addImage(image));

  return gallery;
}
