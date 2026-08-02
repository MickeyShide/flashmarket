import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';

export const StockTab = ({ product, variant = null }) => {
  const { triggerToast } = useToast();
  const [stock, setStock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quantityInput, setQuantityInput] = useState('');
  const [updating, setUpdating] = useState(false);

  const loadStock = useCallback(async () => {
    if (!product?.id) return;
    setLoading(true);
    try {
      const url = variant?.id 
        ? `/api/v1/stocks/${product.id}?variant_id=${variant.id}`
        : `/api/v1/stocks/${product.id}`;
      const data = await apiJson(url);
      setStock(data);
      setQuantityInput(data.total !== undefined ? String(data.total) : '');
    } catch (err) {
      setStock({ total: 0, available: 0, reserved: 0, sold: 0 });
    } finally {
      setLoading(false);
    }
  }, [product?.id, variant?.id]);

  useEffect(() => {
    loadStock();
  }, [loadStock]);

  const handleUpdateStock = async (e) => {
    e.preventDefault();
    if (quantityInput === '') return;

    setUpdating(true);
    try {
      const targetQty = parseInt(quantityInput, 10) || 0;
      if (stock?.id) {
        const suffix = variant?.id ? `?variant_id=${variant.id}` : '';
        await apiJson(`/api/v1/stocks/${product.id}${suffix}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ total: targetQty })
        });
      } else {
        await apiJson('/api/v1/stocks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            product_id: product.id,
            variant_id: variant?.id || null,
            total: targetQty
          })
        });
      }

      triggerToast('Остаток склада обновлен!');
      loadStock();
    } catch (err) {
      triggerToast(err.message || 'Ошибка обновления остатка', true);
    } finally {
      setUpdating(false);
    }
  };

  if (loading) return <div className="spinner"></div>;

  return (
    <div className="bg-white border border-border-color rounded-lg p-5 space-y-4">
      <h3 className="text-sm font-black uppercase">
        Складской учет: {product.name} {variant ? `(${variant.sku || variant.size})` : ''}
      </h3>

      {/* Stock counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 text-center">
        <div className="bg-gray-50 p-2.5 sm:p-3 rounded border">
          <div className="text-[10px] font-bold uppercase text-gray-500">Доступно</div>
          <div className="text-base font-black text-emerald-600">{stock?.available ?? 0}</div>
        </div>
        <div className="bg-gray-50 p-2.5 sm:p-3 rounded border">
          <div className="text-[10px] font-bold uppercase text-gray-500">Зарезервировано</div>
          <div className="text-base font-black text-amber-600">{stock?.reserved ?? 0}</div>
        </div>
        <div className="bg-gray-50 p-2.5 sm:p-3 rounded border">
          <div className="text-[10px] font-bold uppercase text-gray-500">Продано</div>
          <div className="text-base font-black text-blue-600">{stock?.sold ?? 0}</div>
        </div>
        <div className="bg-gray-50 p-2.5 sm:p-3 rounded border">
          <div className="text-[10px] font-bold uppercase text-gray-500">Всего</div>
          <div className="text-base font-black text-black">{stock?.total ?? 0}</div>
        </div>
      </div>

      {/* Form to set available quantity */}
      <form onSubmit={handleUpdateStock} className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-end pt-2">
        <div className="flex-1">
          <label className="block text-[10.5px] font-bold uppercase text-gray-700 mb-1">
            Установить доступное количество на складе (шт.)
          </label>
          <input
            type="number"
            min="0"
            required
            className="w-full border p-2 rounded text-xs font-bold"
            value={quantityInput}
            onChange={(e) => setQuantityInput(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={updating}
          className="bg-black text-white px-4 py-2.5 rounded text-xs font-black uppercase hover:bg-gray-800 disabled:opacity-50"
        >
          {updating ? 'Обновление...' : 'Сохранить остаток'}
        </button>
      </form>
    </div>
  );
};
