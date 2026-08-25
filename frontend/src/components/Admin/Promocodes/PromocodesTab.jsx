import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { formatPrice } from '../../../utils/formatters';
import { usePaginatedResource } from '../../../hooks/usePaginatedResource';
import { InfiniteScrollTrigger } from '../../Common/InfiniteScrollTrigger';
import { AdminTableSkeleton } from '../AdminTableSkeleton';

const PAGE_SIZE = 25;

export const PromocodesTab = () => {
  const { triggerToast } = useToast();
  const [editingPromo, setEditingPromo] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  // Form fields
  const [code, setCode] = useState('');
  const [discountType, setDiscountType] = useState('PERCENTAGE'); // PERCENTAGE | FIXED
  const [currency, setCurrency] = useState('RUB');
  const [discountValue, setDiscountValue] = useState('');
  const [minOrderAmountRub, setMinOrderAmountRub] = useState('');
  const [maxDiscountAmountRub, setMaxDiscountAmountRub] = useState('');
  const [maxUses, setMaxUses] = useState('');
  const [maxUsesPerUser, setMaxUsesPerUser] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchPromocodesPage = useCallback(({ limit, offset, signal }) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return apiJson(`/api/v1/promocodes/?${params}`, { signal });
  }, []);

  const {
    items: promocodes,
    total,
    loading,
    loadingMore,
    error,
    hasMore,
    reload: loadPromocodes,
    loadMore
  } = usePaginatedResource({ fetchPage: fetchPromocodesPage, pageSize: PAGE_SIZE });

  useEffect(() => {
    loadPromocodes();
  }, [loadPromocodes]);

  const handleOpenCreate = () => {
    setEditingPromo(null);
    setIsCreating(true);
    setCode('');
    setDiscountType('PERCENTAGE');
    setCurrency('RUB');
    setDiscountValue('10');
    setMinOrderAmountRub('');
    setMaxDiscountAmountRub('');
    setMaxUses('');
    setMaxUsesPerUser('1');
    setExpiresAt('');
    setStartsAt(new Date().toISOString().slice(0, 16));
    setIsActive(true);
  };

  const handleOpenEdit = (p) => {
    setEditingPromo(p);
    setIsCreating(false);
    setCode(p.code || '');
    setDiscountType(p.discount_type || p.type || 'PERCENTAGE');
    setCurrency(p.currency || 'RUB');

    // Values & Thresholds conversion (rubles vs kopecks)
    const type = p.discount_type || p.type || 'PERCENTAGE';
    if (type === 'FIXED') {
      setDiscountValue(p.discount_value !== undefined ? String(p.discount_value / 100) : '');
    } else {
      setDiscountValue(p.discount_value !== undefined ? String(p.discount_value) : '');
    }

    setMinOrderAmountRub(p.min_order_amount ? String(p.min_order_amount / 100) : '');
    setMaxDiscountAmountRub(p.max_discount_amount ? String(p.max_discount_amount / 100) : '');
    setMaxUses(p.max_uses ? String(p.max_uses) : '');
    setMaxUsesPerUser(p.max_uses_per_user ? String(p.max_uses_per_user) : '');
    setExpiresAt(p.expires_at ? new Date(p.expires_at).toISOString().slice(0, 16) : '');
    setStartsAt(p.starts_at ? new Date(p.starts_at).toISOString().slice(0, 16) : '');
    setIsActive(p.status === 'ACTIVE');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!code.trim() || !discountValue || (!editingPromo && !expiresAt)) {
      triggerToast('Укажите код, скидку и срок действия', true);
      return;
    }

    setSaving(true);
    try {
      const valNum = parseFloat(discountValue);
      const valFinal = discountType === 'FIXED' ? Math.round(valNum * 100) : valNum;

      const body = {
        code: code.trim().toUpperCase(),
        discount_type: discountType,
        discount_value: valFinal,
        status: isActive ? 'ACTIVE' : 'DISABLED',
        currency,
        min_order_amount: minOrderAmountRub ? Math.round(parseFloat(minOrderAmountRub) * 100) : null,
        max_discount_amount: maxDiscountAmountRub ? Math.round(parseFloat(maxDiscountAmountRub) * 100) : null,
        max_uses: maxUses ? parseInt(maxUses, 10) : null,
        max_uses_per_user: maxUsesPerUser ? parseInt(maxUsesPerUser, 10) : null,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        starts_at: startsAt ? new Date(startsAt).toISOString() : undefined
      };

      if (editingPromo) {
        // PATCH /api/v1/promocodes/{id}
        await apiJson(`/api/v1/promocodes/${editingPromo.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        triggerToast('Промокод обновлен!');
      } else {
        // POST /api/v1/promocodes
        await apiJson('/api/v1/promocodes/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        triggerToast('Промокод создан!');
      }

      setEditingPromo(null);
      setIsCreating(false);
      loadPromocodes();
    } catch (err) {
      triggerToast(err.message || 'Ошибка сохранения промокода', true);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleStatus = async (promo) => {
    try {
      await apiJson(`/api/v1/promocodes/${promo.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: promo.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE' })
      });
      triggerToast(`Промокод ${promo.code} ${promo.status !== 'ACTIVE' ? 'активирован' : 'деактивирован'}`);
      loadPromocodes();
    } catch (err) {
      triggerToast(err.message || 'Ошибка изменения статуса промокода', true);
    }
  };

  if (loading) return <AdminTableSkeleton rows={5} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <h3 className="text-sm font-black uppercase">Промокоды ({total})</h3>
        <button
          className="bg-black text-white px-4 py-2 rounded text-xs font-black uppercase tracking-wider hover:bg-gray-800 w-full sm:w-auto cursor-pointer"
          onClick={handleOpenCreate}
        >
          + Создать промокод
        </button>
      </div>

      {error && promocodes.length === 0 && (
        <button className="text-xs font-bold uppercase text-red-700" onClick={loadPromocodes}>Повторить загрузку</button>
      )}

      {/* Create / Edit Form */}
      {(isCreating || editingPromo) && (
        <div className="bg-white border-2 border-black rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <h4 className="text-sm font-black uppercase">
              {isCreating ? 'Создание промокода' : `Редактирование: ${editingPromo.code}`}
            </h4>
            <button className="text-xs font-bold text-gray-500 hover:text-black" onClick={() => { setEditingPromo(null); setIsCreating(false); }}>
              ✕ Закрыть
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold uppercase mb-1">Промокод (Код) *</label>
                <input
                  type="text"
                  required
                  placeholder="FLASH10"
                  className="w-full border p-2 rounded uppercase font-mono font-bold"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Тип скидки *</label>
                <select
                  className="w-full border p-2 rounded font-bold"
                  value={discountType}
                  onChange={(e) => setDiscountType(e.target.value)}
                >
                  <option value="PERCENTAGE">Процентная (%)</option>
                  <option value="FIXED">Фиксированная сумма (₽)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">
                  Значение скидки {discountType === 'PERCENTAGE' ? '(%)' : '(₽)'} *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  className="w-full border p-2 rounded font-bold"
                  value={discountValue}
                  onChange={(e) => setDiscountValue(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Мин. сумма заказа (₽)</label>
                <input
                  type="number"
                  placeholder="без ограничений"
                  className="w-full border p-2 rounded font-bold"
                  value={minOrderAmountRub}
                  onChange={(e) => setMinOrderAmountRub(e.target.value)}
                />
              </div>

              {discountType === 'PERCENTAGE' && (
                <div>
                  <label className="block font-bold uppercase mb-1">Макс. скидка в рублях (₽)</label>
                  <input
                    type="number"
                    placeholder="без лимита"
                    className="w-full border p-2 rounded font-bold"
                    value={maxDiscountAmountRub}
                    onChange={(e) => setMaxDiscountAmountRub(e.target.value)}
                  />
                </div>
              )}

              <div>
                <label className="block font-bold uppercase mb-1">Лимит использований (Всего)</label>
                <input
                  type="number"
                  placeholder="неограниченно"
                  className="w-full border p-2 rounded font-bold"
                  value={maxUses}
                  onChange={(e) => setMaxUses(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Лимит на пользователя</label>
                <input
                  type="number"
                  placeholder="1"
                  className="w-full border p-2 rounded font-bold"
                  value={maxUsesPerUser}
                  onChange={(e) => setMaxUsesPerUser(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Срок действия до</label>
                <input
                  type="datetime-local"
                  className="w-full border p-2 rounded font-mono"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Действует с</label>
                <input
                  type="datetime-local"
                  required
                  className="w-full border p-2 rounded font-mono"
                  value={startsAt}
                  onChange={(e) => setStartsAt(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Валюта</label>
                <input
                  type="text"
                  minLength={3}
                  maxLength={3}
                  required
                  className="w-full border p-2 rounded font-mono uppercase"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="bg-black text-white px-6 py-3 rounded font-black uppercase tracking-wider hover:bg-gray-800 disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : editingPromo ? 'Сохранить промокод' : 'Создать промокод'}
            </button>
          </form>
        </div>
      )}

      {/* Mobile Promocodes Cards List (< md screens) */}
      <div className="md:hidden space-y-3">
        {promocodes.length === 0 ? (
          <div className="bg-white border border-border-color rounded-lg p-6 text-center text-xs text-gray-500">
            Промокоды не найдены
          </div>
        ) : (
          promocodes.map(p => {
            const isFixed = (p.discount_type || p.type) === 'FIXED';
            const displayVal = isFixed ? formatPrice(p.discount_value, 'RUB', true) : `${p.discount_value}%`;

            return (
              <div key={p.id} className="bg-white border border-border-color rounded-lg p-3.5 space-y-3 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-mono font-black text-sm uppercase text-black">{p.code}</h4>
                    <div className="font-extrabold text-xs text-emerald-600 mt-0.5">Скидка: {displayVal}</div>
                  </div>
                  <span className={`text-[8.5px] font-black px-1.5 py-0.5 rounded uppercase shrink-0 ${
                    p.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {p.status === 'ACTIVE' ? 'АКТИВЕН' : 'ОТКЛЮЧЕН'}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[10.5px] font-mono text-gray-600 bg-gray-50 p-2 rounded border">
                  <div>Мин. заказ: {p.min_order_amount ? formatPrice(p.min_order_amount, 'RUB', true) : 'Без мин.'}</div>
                  <div>Использования: {p.current_uses ?? p.used_count ?? 0}/{p.max_uses ? p.max_uses : '∞'}</div>
                </div>

                <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
                  <button
                    className="flex-1 py-2 bg-black text-white text-[11px] font-bold rounded uppercase hover:bg-gray-800 cursor-pointer text-center"
                    onClick={() => handleOpenEdit(p)}
                  >
                    Изменить
                  </button>
                  <button
                    className={`px-3 py-2 text-[11px] font-bold rounded uppercase cursor-pointer ${
                      p.status === 'ACTIVE' ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                    }`}
                    onClick={() => handleToggleStatus(p)}
                  >
                    {p.status === 'ACTIVE' ? 'Отключить' : 'Включить'}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Desktop Promocodes Table (>= md screens) */}
      <div className="hidden md:block bg-white border border-border-color rounded-lg overflow-x-auto w-full">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-[10px] font-black uppercase text-gray-500">
              <th className="p-3">Код</th>
              <th className="p-3">Скидка</th>
              <th className="p-3">Мин. Заказ</th>
              <th className="p-3">Использования</th>
              <th className="p-3">Статус</th>
              <th className="p-3 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs">
            {promocodes.map(p => {
              const isFixed = (p.discount_type || p.type) === 'FIXED';
              const displayVal = isFixed ? formatPrice(p.discount_value, 'RUB', true) : `${p.discount_value}%`;

              return (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="p-3 font-mono font-black uppercase">{p.code}</td>
                  <td className="p-3 font-extrabold text-emerald-600">{displayVal}</td>
                  <td className="p-3 font-mono">
                    {p.min_order_amount ? formatPrice(p.min_order_amount, 'RUB', true) : '-'}
                  </td>
                  <td className="p-3 font-mono">
                    {p.current_uses ?? p.used_count ?? 0} / {p.max_uses ? p.max_uses : '∞'}
                  </td>
                  <td className="p-3">
                    <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase ${
                      p.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {p.status === 'ACTIVE' ? 'АКТИВЕН' : 'ОТКЛЮЧЕН'}
                    </span>
                  </td>
                  <td className="p-3 text-right space-x-1.5">
                    <button
                      className="px-2.5 py-1 bg-black text-white text-[10px] font-bold rounded uppercase hover:bg-gray-800 cursor-pointer"
                      onClick={() => handleOpenEdit(p)}
                    >
                      Изменить
                    </button>
                    <button
                      className={`px-2.5 py-1 text-[10px] font-bold rounded uppercase cursor-pointer ${
                        p.status === 'ACTIVE' ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                      }`}
                      onClick={() => handleToggleStatus(p)}
                    >
                      {p.status === 'ACTIVE' ? 'Отключить' : 'Включить'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <InfiniteScrollTrigger
        hasMore={hasMore}
        loading={loadingMore}
        error={promocodes.length > 0 ? error : null}
        onLoadMore={loadMore}
      />
    </div>
  );
};
