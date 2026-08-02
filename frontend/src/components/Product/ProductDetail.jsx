import React, { useState, useEffect, useMemo } from 'react';
import { apiJson } from '../../services/api';
import { formatPrice } from '../../utils/formatters';
import { useCart } from '../../context/CartContext';
import { useToast } from '../../context/ToastContext';
import { useWishlist } from '../../context/WishlistContext';
import { buildProductGallery } from './productGallery';

export const ProductDetail = ({ productSlug, dropInfo = null, onBack }) => {
  const { addToCart, fetchStock } = useCart();
  const { triggerToast } = useToast();
  const { isWished, toggleWishlist } = useWishlist();

  const [product, setProduct] = useState(null);
  const [selectedImageUrl, setSelectedImageUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedVariant, setSelectedVariant] = useState(null);
  const [selectedSize, setSelectedSize] = useState(null);
  const [selectedColor, setSelectedColor] = useState(null);

  const [stockInfo, setStockInfo] = useState(null);
  const [loadingStock, setLoadingStock] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadProduct() {
      setLoading(true);
      setError(null);
      try {
        const item = await apiJson('/api/v1/products/' + encodeURIComponent(productSlug));
        if (!isMounted) return;
        setProduct(item);
        const firstGalleryImage = buildProductGallery(item.cover_image, item.images)[0]?.url;
        setSelectedImageUrl(firstGalleryImage || null);
        setLoading(false);

        // Derive active variants if available
        const activeVariants = (item.variants || []).filter(v => v.is_active !== false);
        if (activeVariants.length > 0) {
          const initial = activeVariants[0];
          setSelectedVariant(initial);
          setSelectedSize(initial.size || initial.attributes?.size || null);
          setSelectedColor(initial.color || initial.attributes?.color || null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
          triggerToast('Не удалось загрузить товар', true);
        }
      }
    }

    if (productSlug) {
      loadProduct();
    }
  }, [productSlug, triggerToast]);

  // Available sizes & colors from active variants
  const activeVariants = useMemo(() => {
    return (product?.variants || []).filter(v => v.is_active !== false);
  }, [product]);

  const galleryImages = useMemo(() => {
    return buildProductGallery(product?.cover_image, product?.images);
  }, [product?.cover_image, product?.images]);

  const availableSizes = useMemo(() => {
    const set = new Set();
    activeVariants.forEach(v => {
      const s = v.size || v.attributes?.size;
      if (s) set.add(s);
    });
    return Array.from(set);
  }, [activeVariants]);

  const availableColors = useMemo(() => {
    const set = new Set();
    activeVariants.forEach(v => {
      const c = v.color || v.attributes?.color;
      if (c) set.add(c);
    });
    return Array.from(set);
  }, [activeVariants]);

  // Handle variant selection update
  const handleSelectSizeColor = (size, color) => {
    const match = activeVariants.find(v => {
      const vSize = v.size || v.attributes?.size;
      const vColor = v.color || v.attributes?.color;
      const matchSize = !size || vSize === size;
      const matchColor = !color || vColor === color;
      return matchSize && matchColor;
    }) || activeVariants.find(v => !size || (v.size || v.attributes?.size) === size)
      || activeVariants.find(v => !color || (v.color || v.attributes?.color) === color)
      || activeVariants[0]
      || null;

    setSelectedVariant(match);
    setSelectedSize(match?.size || match?.attributes?.size || null);
    setSelectedColor(match?.color || match?.attributes?.color || null);
  };

  // Fetch stock when selected variant changes
  useEffect(() => {
    let isMounted = true;
    async function loadStock() {
      if (!product) return;
      setLoadingStock(true);
      try {
        const variantId = selectedVariant?.id || null;
        const stock = await fetchStock(product.id, variantId);
        if (isMounted) {
          setStockInfo(stock);
          setLoadingStock(false);
        }
      } catch (err) {
        if (isMounted) {
          setStockInfo({ total: 0, available: 0, reserved: 0, sold: 0 });
          setLoadingStock(false);
        }
      }
    }
    loadStock();
  }, [product, selectedVariant, fetchStock]);

  if (loading) {
    return (
      <div className="max-w-[1040px] mx-auto my-8 px-4">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад в каталог
        </button>
        <div className="spinner"></div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="max-w-[1040px] mx-auto my-8 px-4">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад в каталог
        </button>
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-lg text-center">
          <div className="font-bold text-sm mb-2">Ошибка загрузки товара</div>
          <div>{error || 'Товар не найден'}</div>
        </div>
      </div>
    );
  }

  const wished = isWished(product.id);
  const bName = product.brand_name ? product.brand_name.toUpperCase() : 'FLASH MARKET';
  const cName = product.category_name ? product.category_name.toUpperCase() : '';
  const available = stockInfo?.available ?? 0;

  const displayPrice = selectedVariant?.effective_price !== undefined && selectedVariant?.effective_price !== null
    ? selectedVariant.effective_price
    : product.price;

  const isAddToCartDisabled = loadingStock || available <= 0;

  return (
    <div className="max-w-[1040px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      {/* Back button & Wishlist heart */}
      <div className="flex items-center justify-between mb-6">
        <button
          className="text-[11px] font-bold uppercase tracking-wider cursor-pointer text-text-muted hover:text-black flex items-center gap-1"
          onClick={onBack}
        >
          ← Назад
        </button>

        <button
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-extrabold transition-colors ${
            wished ? 'border-red-200 bg-red-50 text-red-600' : 'border-gray-300 bg-white text-gray-700 hover:border-black'
          }`}
          onClick={() => toggleWishlist(product.id)}
        >
          <svg
            className={`w-4 h-4 ${wished ? 'fill-red-500 stroke-red-500' : 'fill-none stroke-current stroke-2'}`}
            viewBox="0 0 24 24"
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
          <span>{wished ? 'В ИЗБРАННОМ' : 'В ИЗБРАННОЕ'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-2 md:gap-9">
        {/* Left: Product gallery */}
        <div className="min-w-0">
          <div
            className="w-full h-[280px] md:h-[420px] bg-black rounded flex flex-col items-center justify-center relative overflow-hidden"
            style={selectedImageUrl ? { background: `url(${selectedImageUrl}) center/cover no-repeat #000` } : {}}
          >
            {!selectedImageUrl && (
              <>
                <svg className="w-16 h-16 stroke-white stroke-[1.2] fill-none opacity-90 mb-2" viewBox="0 0 24 24">
                  <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
                </svg>
                <span className="font-mono text-xs tracking-[2px] text-[#666666] uppercase">
                  {bName}
                </span>
              </>
            )}

            {dropInfo && (
              <div className="absolute top-3 left-3 bg-purple-600 text-white font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-1 rounded shadow">
                DROP: {dropInfo.name || dropInfo.slug}
              </div>
            )}
          </div>

          {galleryImages.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {galleryImages.map(image => (
                <button
                  key={image.id || image.url}
                  type="button"
                  aria-label={image.isCover ? 'Выбрать обложку товара' : 'Выбрать изображение товара'}
                  className={`w-14 h-14 rounded overflow-hidden border ${selectedImageUrl === image.url ? 'border-black' : 'border-border-color'}`}
                  onClick={() => setSelectedImageUrl(image.url)}
                >
                  <img
                    src={image.url}
                    alt={image.isCover ? 'Обложка товара' : ''}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Info & Controls */}
        <div className="flex min-w-0 flex-col justify-start">
          <div className="text-[10.5px] font-extrabold tracking-[2px] uppercase text-text-muted mb-1.5 flex items-center gap-2">
            <span>{bName}{cName ? ' / ' + cName : ''}</span>
            {selectedVariant?.sku && <span className="font-mono text-[9px]">SKU: {selectedVariant.sku}</span>}
          </div>

          <h2 className="text-xl md:text-2xl font-black tracking-wide uppercase mb-2">
            {product.name}
          </h2>

          <div className="text-lg md:text-2xl font-black mb-4 text-black">
            {formatPrice(displayPrice, product.currency || 'RUB', false)}
          </div>

          <div className="text-xs text-gray-600 mb-6 leading-relaxed">
            {product.description || 'Описание товара появится позже.'}
          </div>

          {selectedVariant?.material && (
            <div className="text-[10.5px] text-gray-500 font-mono mb-4">
              Материал: {selectedVariant.material}
            </div>
          )}

          {/* Size selector if available */}
          {availableSizes.length > 0 && (
            <div className="mb-4">
              <label className="text-[10.5px] font-extrabold uppercase tracking-wider mb-2 block">
                Размер: {selectedSize}
              </label>
              <div className="flex flex-wrap gap-2">
                {availableSizes.map(sz => (
                  <button
                    key={sz}
                    className={`min-w-[42px] h-10 px-3 border rounded text-xs font-extrabold flex items-center justify-center cursor-pointer transition-colors ${
                      selectedSize === sz
                        ? 'bg-black text-white border-black'
                        : 'border-border-color bg-white text-black hover:border-black'
                    }`}
                    onClick={() => handleSelectSizeColor(sz, selectedColor)}
                  >
                    {sz}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Color selector if available */}
          {availableColors.length > 0 && (
            <div className="mb-5">
              <label className="text-[10.5px] font-extrabold uppercase tracking-wider mb-2 block">
                Цвет: {selectedColor}
              </label>
              <div className="flex flex-wrap gap-2">
                {availableColors.map(col => (
                  <button
                    key={col}
                    className={`px-3 py-2 border rounded text-xs font-extrabold flex items-center justify-center cursor-pointer transition-colors ${
                      selectedColor === col
                        ? 'bg-black text-white border-black'
                        : 'border-border-color bg-white text-black hover:border-black'
                    }`}
                    onClick={() => handleSelectSizeColor(selectedSize, col)}
                  >
                    {col}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Stock Info Badge */}
          <div className="mb-6">
            {loadingStock ? (
              <div className="stock-badge unknown-stock">Проверяем наличие…</div>
            ) : available > 10 ? (
              <div className="stock-badge in-stock">✓ В наличии</div>
            ) : available > 0 ? (
              <div className="stock-badge low-stock">⚠ Осталось {available} шт.</div>
            ) : stockInfo ? (
              <div className="stock-badge out-of-stock">✕ Нет в наличии</div>
            ) : (
              <div className="stock-badge unknown-stock">Информация о наличии недоступна</div>
            )}
          </div>

          {/* Add to Cart Button */}
          <button
            className="w-full bg-black text-white py-4 px-6 text-xs font-black tracking-[1.5px] uppercase cursor-pointer rounded hover:bg-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={isAddToCartDisabled}
            onClick={() => addToCart(product, selectedVariant || { size: selectedSize || 'OS' }, dropInfo, 1)}
          >
            {isAddToCartDisabled
              ? (available === 0 ? 'НЕТ В НАЛИЧИИ' : 'НЕДОСТУПНО')
              : 'ДОБАВИТЬ В КОРЗИНУ'}
          </button>
        </div>
      </div>
    </div>
  );
};
