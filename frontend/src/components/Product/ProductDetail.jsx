import React, { useState, useEffect } from 'react';
import { apiJson } from '../../services/api';
import { formatPrice } from '../../utils/formatters';
import { useCart } from '../../context/CartContext';
import { useToast } from '../../context/ToastContext';

export const ProductDetail = ({ productSlug, onBack }) => {
  const { addToCartCurrent, fetchStock, stockCache } = useCart();
  const { triggerToast } = useToast();

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedSize, setSelectedSize] = useState('OS');
  const [stockInfo, setStockInfo] = useState(null);
  const [loadingStock, setLoadingStock] = useState(true);

  const sizes = ['S', 'M', 'L', 'XL', 'OS'];

  useEffect(() => {
    let isMounted = true;
    async function loadProduct() {
      setLoading(true);
      setError(null);
      try {
        const item = await apiJson('/api/v1/products/' + encodeURIComponent(productSlug));
        if (!isMounted) return;
        setProduct(item);
        setLoading(false);

        // Fetch live stock
        setLoadingStock(true);
        const stock = await fetchStock(item.id);
        if (isMounted) {
          setStockInfo(stock);
          setLoadingStock(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
          setLoadingStock(false);
          triggerToast('Не удалось загрузить товар', true);
        }
      }
    }

    if (productSlug) {
      loadProduct();
    }
  }, [productSlug, fetchStock, triggerToast]);

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

  const bName = product.brand_name ? product.brand_name.toUpperCase() : 'FLASH MARKET';
  const cName = product.category_name ? product.category_name.toUpperCase() : '';
  const available = stockInfo?.available ?? 0;

  const isAddToCartDisabled = loadingStock || available <= 0;

  return (
    <div className="max-w-[1040px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      {/* Back button */}
      <button
        className="text-[11px] font-bold uppercase tracking-wider mb-6 cursor-pointer text-text-muted hover:text-black flex items-center gap-1"
        onClick={onBack}
      >
        ← Назад в каталог
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-9">
        {/* Left: Product Image Box */}
        <div
          className="w-full h-[240px] md:h-[380px] bg-black rounded flex flex-col items-center justify-center relative overflow-hidden"
          style={product.cover_image ? { background: `url(${product.cover_image}) center/cover no-repeat #000` } : {}}
        >
          {!product.cover_image && (
            <>
              <svg className="w-16 h-16 stroke-white stroke-[1.2] fill-none opacity-90 mb-2" viewBox="0 0 24 24">
                <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
              </svg>
              <span className="font-mono text-xs tracking-[2px] text-[#666666] uppercase">
                {bName}
              </span>
            </>
          )}
        </div>

        {/* Right: Info & Controls */}
        <div className="flex flex-col justify-center">
          <div className="text-[10.5px] font-extrabold tracking-[2px] uppercase text-text-muted mb-1.5">
            {bName}{cName ? ' / ' + cName : ''} / {product.status}
          </div>

          <h2 className="text-xl md:text-2xl font-black tracking-wide uppercase mb-2">
            {product.name}
          </h2>

          {product.status !== 'ACTIVE' && (
            <div className="mb-3">
              <span className="status-badge">СТАТУС: {product.status}</span>
            </div>
          )}

          <div className="text-lg md:text-xl font-extrabold mb-4">
            {formatPrice(product.price, product.currency, false)}
          </div>

          <div className="text-xs text-gray-600 mb-6 leading-relaxed">
            {product.description || 'Описание появится позже.'}
          </div>

          {/* Size selector */}
          <div className="mb-5">
            <label className="text-[10.5px] font-extrabold uppercase tracking-wider mb-2 block">
              Размер:
            </label>
            <div className="flex gap-2">
              {sizes.map(size => (
                <button
                  key={size}
                  className={`w-10.5 h-10.5 border rounded text-xs font-extrabold flex items-center justify-center cursor-pointer transition-colors ${
                    selectedSize === size
                      ? 'bg-black text-white border-black'
                      : 'border-border-color bg-white text-black hover:border-black'
                  }`}
                  onClick={() => setSelectedSize(size)}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>

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
            onClick={() => addToCartCurrent(product, selectedSize)}
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
