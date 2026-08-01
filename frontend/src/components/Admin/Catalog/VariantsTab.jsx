import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { StockTab } from '../Inventory/StockTab';

export const VariantsTab = ({ product, onProductUpdated }) => {
  const { triggerToast } = useToast();
  const [variants, setVariants] = useState([]);
  const [loading, setLoading] = useState(true);

  const [sku, setSku] = useState('');
  const [size, setSize] = useState('');
  const [color, setColor] = useState('');
  const [effectivePrice, setEffectivePrice] = useState('');
  const [saving, setSaving] = useState(false);
  const [stockVariant, setStockVariant] = useState(null);

  const loadVariants = useCallback(async () => {
    if (!product?.id) return;
    setLoading(true);
    try {
      const data = await apiJson(`/api/v1/products/${product.id}/variants/`).catch(async () => {
        // Fallback: check product.variants
        const p = await apiJson(`/api/v1/products/${product.id}`);
        return p.variants || [];
      });
      setVariants(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.warn('Failed to load variants:', err);
    } finally {
      setLoading(false);
    }
  }, [product?.id]);

  useEffect(() => {
    loadVariants();
  }, [loadVariants]);

  const handleCreateVariant = async (e) => {
    e.preventDefault();
    if (!sku.trim()) return;

    setSaving(true);
    try {
      const body = {
        sku: sku.trim().toUpperCase(),
        size: size.trim() || null,
        color: color.trim() || null,
        is_active: true
      };
      if (effectivePrice) {
        body.price_override = parseFloat(effectivePrice);
      }

      await apiJson(`/api/v1/products/${product.id}/variants/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      triggerToast('Вариант создан!');
      setSku('');
      setSize('');
      setColor('');
      setEffectivePrice('');
      loadVariants();
      if (onProductUpdated) onProductUpdated();
    } catch (err) {
      triggerToast(err.message || 'Ошибка создания варианта', true);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteVariant = async (variantId) => {
    if (!window.confirm('Удалить этот вариант товара?')) return;
    try {
      await apiJson(`/api/v1/products/${product.id}/variants/${variantId}`, {
        method: 'DELETE'
      });
      triggerToast('Вариант удален');
      loadVariants();
      if (onProductUpdated) onProductUpdated();
    } catch (err) {
      triggerToast(err.message || 'Ошибка удаления варианта', true);
    }
  };

  const handleEditVariant = async (variant) => {
    const nextSku = window.prompt('SKU', variant.sku || '');
    if (nextSku === null || !nextSku.trim()) return;
    const nextSize = window.prompt('Размер', variant.size || '');
    if (nextSize === null) return;
    const nextColor = window.prompt('Цвет', variant.color || '');
    if (nextColor === null) return;
    const nextPrice = window.prompt('Цена варианта (пусто = базовая)', variant.price_override ?? '');
    if (nextPrice === null) return;
    const nextOrder = window.prompt('Порядок', String(variant.sort_order ?? 0));
    if (nextOrder === null) return;
    try {
      await apiJson(`/api/v1/products/${product.id}/variants/${variant.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sku: nextSku.trim().toUpperCase(),
          size: nextSize.trim() || null,
          color: nextColor.trim() || null,
          price_override: nextPrice.trim() ? parseFloat(nextPrice) : null,
          sort_order: Math.max(0, parseInt(nextOrder, 10) || 0)
        })
      });
      triggerToast('Вариант обновлен');
      loadVariants();
    } catch (err) {
      triggerToast(err.message || 'Ошибка обновления варианта', true);
    }
  };

  const handleToggleVariant = async (variant) => {
    try {
      await apiJson(`/api/v1/products/${product.id}/variants/${variant.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: variant.is_active === false })
      });
      loadVariants();
    } catch (err) {
      triggerToast(err.message || 'Ошибка статуса варианта', true);
    }
  };

  if (loading) return <div className="spinner"></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-black uppercase">Варианты товара ({variants.length})</h4>
      </div>

      {variants.length === 0 ? (
        <div className="text-xs text-gray-500 py-3 bg-gray-50 p-3 rounded">
          У товара пока нет вариантов (используются свойства базового товара)
        </div>
      ) : (
        <div className="divide-y divide-gray-100 border rounded p-3 bg-white">
          {variants.map(v => (
            <div key={v.id} className="py-2 flex items-center justify-between text-xs">
              <div>
                <span className="font-extrabold font-mono uppercase">{v.sku}</span>
                <span className="ml-2 text-gray-600">
                  {v.size && `Размер: ${v.size} `}
                  {v.color && `· Цвет: ${v.color} `}
                  {v.effective_price !== undefined && v.effective_price !== null && `· Цена: ${v.effective_price} ₽`}
                </span>
              </div>
              <div className="flex gap-2">
                <button className="text-[10px] font-bold uppercase" onClick={() => handleEditVariant(v)}>Изменить</button>
                <button className="text-[10px] font-bold uppercase" onClick={() => handleToggleVariant(v)}>
                  {v.is_active === false ? 'Включить' : 'Отключить'}
                </button>
                <button className="text-[10px] font-bold uppercase" onClick={() => setStockVariant(v)}>Склад</button>
                <button
                  className="text-[10px] text-red-600 hover:text-red-800 font-bold uppercase"
                  onClick={() => handleDeleteVariant(v.id)}
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {stockVariant && (
        <div>
          <button className="text-[10px] font-bold uppercase mb-2" onClick={() => setStockVariant(null)}>✕ Закрыть склад варианта</button>
          <StockTab product={product} variant={stockVariant} />
        </div>
      )}

      {/* Create form */}
      <form onSubmit={handleCreateVariant} className="bg-gray-50 border rounded p-3 space-y-3 text-xs">
        <div className="font-extrabold uppercase text-[11px]">Добавить вариант</div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-[10px] font-bold uppercase mb-1">SKU *</label>
            <input
              type="text"
              required
              placeholder="SKU-001-S"
              className="w-full border p-1.5 rounded uppercase font-mono text-[11px]"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold uppercase mb-1">Размер</label>
            <input
              type="text"
              placeholder="S, M, L, XL..."
              className="w-full border p-1.5 rounded text-[11px]"
              value={size}
              onChange={(e) => setSize(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold uppercase mb-1">Цвет</label>
            <input
              type="text"
              placeholder="Black, White..."
              className="w-full border p-1.5 rounded text-[11px]"
              value={color}
              onChange={(e) => setColor(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold uppercase mb-1">Цена варианта (необязательно)</label>
            <input
              type="number"
              placeholder="оставьте пустым для цены товара"
              className="w-full border p-1.5 rounded text-[11px]"
              value={effectivePrice}
              onChange={(e) => setEffectivePrice(e.target.value)}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="bg-black text-white px-4 py-2 rounded text-[10.5px] font-bold uppercase hover:bg-gray-800 disabled:opacity-50"
        >
          {saving ? 'Сохранение...' : '+ Добавить вариант'}
        </button>
      </form>
    </div>
  );
};
