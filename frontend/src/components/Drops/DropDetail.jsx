import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../services/api';
import { ProductCard } from '../Catalog/ProductCard';
import { Countdown } from './Countdown';
import { useToast } from '../../context/ToastContext';
import { DropDetailSkeleton } from './DropDetailSkeleton';

export const DropDetail = ({ dropIdentifier, onOpenProductWithDrop, onBack }) => {
  const { triggerToast } = useToast();
  const [drop, setDrop] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDrop = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Try by ID endpoint first or slug
      const isUuid = /^[0-9a-fA-F-]{36}$/.test(dropIdentifier);
      const url = isUuid ? `/api/v1/drops/id/${dropIdentifier}` : `/api/v1/drops/${encodeURIComponent(dropIdentifier)}`;
      const data = await apiJson(url);

      setDrop(data);

      // Extract product IDs
      let productIds = [];
      if (Array.isArray(data.items)) {
        productIds = data.items.map(item => item.product_id || item.id || item);
      } else if (Array.isArray(data.product_ids)) {
        productIds = data.product_ids;
      }

      if (productIds.length > 0) {
        // Batch hydrate products
        const hydrated = await apiJson('/api/v1/products/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_ids: productIds })
        });

        const list = Array.isArray(hydrated) ? hydrated : (hydrated.items || []);
        setProducts(list);
      } else {
        setProducts([]);
      }
    } catch (err) {
      setError(err.message || 'Дроп не найден');
      triggerToast('Не удалось загрузить информацию о дропе', true);
    } finally {
      setLoading(false);
    }
  }, [dropIdentifier, triggerToast]);

  useEffect(() => {
    if (dropIdentifier) {
      loadDrop();
    }
  }, [dropIdentifier, loadDrop]);

  if (loading) {
    return <DropDetailSkeleton onBack={onBack} />;
  }

  if (error || !drop) {
    return (
      <div className="max-w-[1280px] mx-auto my-8 px-4">
        <button className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black" onClick={onBack}>
          ← Назад в каталог
        </button>
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-lg text-center">
          <div className="font-bold text-sm mb-2">Ошибка загрузки дропа</div>
          <div>{error || 'Дроп не найден'}</div>
        </div>
      </div>
    );
  }

  const isScheduled = drop.status === 'SCHEDULED' || (drop.status !== 'DRAFT' && drop.status !== 'ENDED' && drop.status !== 'CANCELLED' && drop.starts_at && new Date(drop.starts_at) > new Date());
  const isActive = drop.status === 'ACTIVE';
  const targetDate = isScheduled ? drop.starts_at : (isActive ? drop.ends_at : null);
  const countdownLabel = isScheduled ? 'До старта:' : 'До окончания:';

  return (
    <div className="max-w-[1280px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      <button
        className="text-[11px] font-bold uppercase tracking-wider mb-6 cursor-pointer text-text-muted hover:text-black flex items-center gap-1"
        onClick={onBack}
      >
        ← Назад
      </button>

      {/* Hero Drop Header Banner */}
      <div className="bg-black text-white rounded-lg p-6 md:p-10 mb-8 relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="z-10 max-w-2xl">
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-[10px] font-black tracking-wider uppercase px-2.5 py-1 rounded ${
              isActive ? 'bg-emerald-500 text-white' : 'bg-purple-600 text-white'
            }`}>
              {isActive ? '● АКТИВНЫЙ ДРОП' : 'АНОНС ДРОПА'}
            </span>

            {drop.max_per_user && (
              <span className="text-[10px] font-extrabold bg-white/20 px-2.5 py-1 rounded">
                Макс: {drop.max_per_user} шт / пользователь
              </span>
            )}

            {drop.payment_timeout_seconds && (
              <span className="text-[10px] font-mono text-gray-300 bg-white/10 px-2.5 py-1 rounded">
                Оплата: {Math.round(drop.payment_timeout_seconds / 60)} мин
              </span>
            )}
          </div>

          <h1 className="text-2xl md:text-4xl font-black uppercase tracking-wide mb-3">
            {drop.name || drop.title || drop.slug}
          </h1>

          {drop.description && (
            <p className="text-xs md:text-sm text-gray-300 leading-relaxed">
              {drop.description}
            </p>
          )}
        </div>

        {targetDate && (
          <div className="z-10 bg-white/10 backdrop-blur border border-white/20 rounded-lg p-4 flex flex-col items-center shrink-0">
            <span className="text-[10px] font-bold text-gray-300 uppercase mb-2">{countdownLabel}</span>
            <Countdown targetDate={targetDate} onExpire={loadDrop} />
          </div>
        )}
      </div>

      {/* Drop Products Grid */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-black uppercase tracking-wider">
          ТОВАРЫ ИЗ ДРОПА ({products.length})
        </h2>
      </div>

      {products.length === 0 ? (
        <div className="bg-gray-50 border border-border-color rounded-lg p-8 text-center text-gray-500 text-sm">
          В этом дропе пока нет товаров
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 md:gap-6">
          {products.map(product => (
            <ProductCard
              key={product.id}
              product={product}
              onClick={() => onOpenProductWithDrop(product.slug || product.id, drop)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
