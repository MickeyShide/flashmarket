import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { MediaUploader } from '../../Media/MediaUploader';

export const DropsTab = () => {
  const { triggerToast } = useToast();
  const [drops, setDrops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('ALL');

  const [editingDrop, setEditingDrop] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  // Form State
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [maxPerUser, setMaxPerUser] = useState('');
  const [paymentTimeoutSeconds, setPaymentTimeoutSeconds] = useState('1800');
  const [coverImage, setCoverImage] = useState('');
  const [saving, setSaving] = useState(false);

  // Product addition state
  const [allProducts, setAllProducts] = useState([]);
  const [searchProductQuery, setSearchProductQuery] = useState('');
  const [dropItems, setDropItems] = useState([]); // [{ product_id, order }]

  const loadDrops = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiJson('/api/v1/admin/drops/?limit=100');
      setDrops(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.warn('Failed to load drops:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProducts = useCallback(async () => {
    try {
      const data = await apiJson('/api/v1/products?limit=100');
      setAllProducts(Array.isArray(data) ? data : (data.items || []));
    } catch (e) {}
  }, []);

  useEffect(() => {
    loadDrops();
    loadProducts();
  }, [loadDrops, loadProducts]);

  const handleOpenCreate = () => {
    setEditingDrop(null);
    setIsCreating(true);
    setName('');
    setSlug('');
    setDescription('');
    setStartsAt('');
    setEndsAt('');
    setMaxPerUser('2');
    setPaymentTimeoutSeconds('1800');
    setCoverImage('');
    setDropItems([]);
  };

  const handleOpenEdit = (drop) => {
    setEditingDrop(drop);
    setIsCreating(false);
    setName(drop.name || drop.title || '');
    setSlug(drop.slug || '');
    setDescription(drop.description || '');
    setStartsAt(drop.starts_at ? new Date(drop.starts_at).toISOString().slice(0, 16) : '');
    setEndsAt(drop.ends_at ? new Date(drop.ends_at).toISOString().slice(0, 16) : '');
    setMaxPerUser(drop.max_per_user ? String(drop.max_per_user) : '');
    setPaymentTimeoutSeconds(drop.payment_timeout_seconds ? String(drop.payment_timeout_seconds) : '1800');
    setCoverImage(drop.cover_image || '');

    const items = (drop.items || []).map((it, idx) => ({
      product_id: it.product_id || it.id || it,
      order: it.sort_order ?? idx
    }));
    setDropItems(items);
  };

  const handleAddProductToDrop = (productId) => {
    if (dropItems.some(i => i.product_id === productId)) {
      triggerToast('Товар уже добавлен в дроп', true);
      return;
    }
    setDropItems(prev => [...prev, { product_id: productId, order: prev.length }]);
  };

  const handleRemoveProductFromDrop = (productId) => {
    setDropItems(prev => prev.filter(i => i.product_id !== productId));
  };

  const handleOrderChange = (productId, newOrder) => {
    setDropItems(prev => prev.map(i => i.product_id === productId ? { ...i, order: parseInt(newOrder, 10) || 0 } : i));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !slug.trim() || !startsAt || !endsAt) {
      triggerToast('Заполните название, slug и даты дропа', true);
      return;
    }

    setSaving(true);
    try {
      const body = {
        name: name.trim(),
        description: description.trim(),
        cover_image: coverImage || null,
        max_per_user: maxPerUser ? parseInt(maxPerUser, 10) : null,
        payment_timeout_seconds: paymentTimeoutSeconds ? parseInt(paymentTimeoutSeconds, 10) : 1800
      };
      if (slug.trim()) body.slug = slug.trim();
      if (startsAt) body.starts_at = new Date(startsAt).toISOString();
      if (endsAt) body.ends_at = new Date(endsAt).toISOString();

      let savedDrop;
      if (editingDrop) {
        savedDrop = await apiJson(`/api/v1/admin/drops/${editingDrop.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        triggerToast('Дроп обновлен!');
      } else {
        savedDrop = await apiJson('/api/v1/admin/drops/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        triggerToast('Дроп создан!');
      }

      for (const item of (savedDrop.items || [])) {
        await apiJson(`/api/v1/admin/drops/${savedDrop.id}/items/${item.product_id}`, {
          method: 'DELETE'
        });
      }
      for (const [index, item] of dropItems.entries()) {
        await apiJson(`/api/v1/admin/drops/${savedDrop.id}/items`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: item.product_id, sort_order: item.order ?? index })
        });
      }

      setEditingDrop(null);
      setIsCreating(false);
      loadDrops();
    } catch (err) {
      triggerToast(err.message || 'Ошибка сохранения дропа', true);
    } finally {
      setSaving(false);
    }
  };

  const handleTransition = async (dropId, actionName) => {
    if (!window.confirm(`Выполнить действие "${actionName}" для дропа?`)) return;
    try {
      await apiJson(`/api/v1/admin/drops/${dropId}/${actionName}`, {
        method: 'POST'
      });

      triggerToast(`Статус дропа изменен: ${actionName}`);
      loadDrops();
    } catch (err) {
      triggerToast(err.message || 'Ошибка изменения статуса дропа', true);
    }
  };

  const filteredDrops = drops.filter(d => filterStatus === 'ALL' || d.status === filterStatus);

  if (loading) return <div className="spinner"></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-black uppercase">Управление дропами ({drops.length})</h3>
          <select
            className="border p-1.5 rounded text-xs font-bold uppercase"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="ALL">Все статусы</option>
            <option value="DRAFT">DRAFT</option>
            <option value="SCHEDULED">SCHEDULED</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="ENDED">ENDED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
        </div>

        <button
          className="bg-black text-white px-4 py-2 rounded text-xs font-black uppercase tracking-wider hover:bg-gray-800"
          onClick={handleOpenCreate}
        >
          + Создать Дроп
        </button>
      </div>

      {/* Form modal/card */}
      {(isCreating || editingDrop) && (
        <div className="bg-white border-2 border-black rounded-lg p-6 space-y-6">
          <div className="flex items-center justify-between border-b pb-3">
            <h4 className="text-sm font-black uppercase">
              {isCreating ? 'Новый дроп (По умолчанию DRAFT)' : `Редактирование дропа: ${editingDrop.name}`}
            </h4>
            <button className="text-xs font-bold text-gray-500 hover:text-black" onClick={() => { setEditingDrop(null); setIsCreating(false); }}>
              ✕ Закрыть
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold uppercase mb-1">Название дропа *</label>
                <input
                  type="text"
                  required
                  className="w-full border p-2 rounded font-sans"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Slug</label>
                <input
                  type="text"
                  className="w-full border p-2 rounded font-mono text-[11px]"
                  placeholder="автогенерация из названия"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Дата и время старта</label>
                <input
                  type="datetime-local"
                  className="w-full border p-2 rounded font-mono"
                  value={startsAt}
                  onChange={(e) => setStartsAt(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Дата и время окончания</label>
                <input
                  type="datetime-local"
                  className="w-full border p-2 rounded font-mono"
                  value={endsAt}
                  onChange={(e) => setEndsAt(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Лимит на пользователя (шт.)</label>
                <input
                  type="number"
                  min="1"
                  className="w-full border p-2 rounded font-bold"
                  value={maxPerUser}
                  onChange={(e) => setMaxPerUser(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Таймаут оплаты (секунды)</label>
                <input
                  type="number"
                  min="60"
                  className="w-full border p-2 rounded font-mono"
                  value={paymentTimeoutSeconds}
                  onChange={(e) => setPaymentTimeoutSeconds(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">Описание дропа</label>
              <textarea
                className="w-full border p-2 rounded font-sans"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">Обложка дропа</label>
              {editingDrop ? (
                <MediaUploader
                  purpose="drop_image"
                  entityType="drop"
                  entityId={editingDrop.id}
                  currentUrl={coverImage}
                  onSuccess={(url) => setCoverImage(url)}
                  label="Загрузить баннер дропа"
                />
              ) : <div className="text-[10px] text-gray-500">Сначала создайте дроп</div>}
            </div>

            {/* Product items in drop */}
            <div className="border-t pt-4 space-y-3">
              <h5 className="font-black uppercase text-xs">Товары в дропе ({dropItems.length})</h5>

              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Поиск товара для добавления..."
                  className="flex-1 border p-2 rounded text-xs"
                  value={searchProductQuery}
                  onChange={(e) => setSearchProductQuery(e.target.value)}
                />
              </div>

              {/* Product search picker dropdown */}
              {searchProductQuery && (
                <div className="max-h-40 overflow-y-auto border rounded bg-white divide-y text-xs">
                  {allProducts
                    .filter(p => p.name.toLowerCase().includes(searchProductQuery.toLowerCase()))
                    .map(p => (
                      <div key={p.id} className="p-2 flex items-center justify-between hover:bg-gray-50">
                        <span>{p.name} ({p.price} ₽)</span>
                        <button
                          type="button"
                          className="bg-black text-white px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                          onClick={() => {
                            handleAddProductToDrop(p.id);
                            setSearchProductQuery('');
                          }}
                        >
                          + Добавить
                        </button>
                      </div>
                    ))}
                </div>
              )}

              {/* Added products list */}
              <div className="space-y-2">
                {dropItems.map(item => {
                  const prod = allProducts.find(p => p.id === item.product_id);
                  return (
                    <div key={item.product_id} className="flex items-center justify-between p-2 border rounded bg-gray-50 text-xs">
                      <div>
                        <span className="font-extrabold uppercase">{prod?.name || item.product_id}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-1 text-[10px] font-bold">
                          Порядок:
                          <input
                            type="number"
                            className="w-12 border p-1 rounded font-bold text-center"
                            value={item.order}
                            onChange={(e) => handleOrderChange(item.product_id, e.target.value)}
                          />
                        </label>
                        <button
                          type="button"
                          className="text-red-600 font-bold text-[10px] uppercase hover:underline"
                          onClick={() => handleRemoveProductFromDrop(item.product_id)}
                        >
                          Удалить
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="bg-black text-white px-6 py-3 rounded font-black uppercase tracking-wider hover:bg-gray-800 disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : editingDrop ? 'Сохранить изменения' : 'Создать дроп'}
            </button>
          </form>
        </div>
      )}

      {/* Drops Table */}
      <div className="bg-white border border-border-color rounded-lg overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-[10px] font-black uppercase text-gray-500">
              <th className="p-3">Дроп</th>
              <th className="p-3">Статус</th>
              <th className="p-3">Старт / Окончание</th>
              <th className="p-3">Товары</th>
              <th className="p-3 text-right">Действия &amp; Переходы</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs">
            {filteredDrops.map(d => (
              <tr key={d.id} className="hover:bg-gray-50 transition-colors">
                <td className="p-3 font-extrabold uppercase">
                  <div>{d.name || d.title || d.slug}</div>
                  <div className="text-[10px] text-gray-400 font-mono">slug: {d.slug}</div>
                </td>
                <td className="p-3">
                  <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase ${
                    d.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' :
                    d.status === 'SCHEDULED' ? 'bg-purple-100 text-purple-800' : 'bg-gray-200 text-gray-700'
                  }`}>
                    {d.status}
                  </span>
                </td>
                <td className="p-3 font-mono text-[10.5px]">
                  <div>{d.starts_at ? new Date(d.starts_at).toLocaleString() : '-'}</div>
                  <div className="text-gray-400">{d.ends_at ? new Date(d.ends_at).toLocaleString() : '-'}</div>
                </td>
                <td className="p-3 font-bold">{d.items?.length || d.product_ids?.length || 0} шт</td>
                <td className="p-3 text-right space-x-1.5">
                  {(d.status === 'DRAFT' || d.status === 'SCHEDULED') && (
                    <button
                      className="px-2.5 py-1 bg-black text-white text-[10px] font-bold rounded uppercase hover:bg-gray-800"
                      onClick={() => handleOpenEdit(d)}
                    >
                      Изменить
                    </button>
                  )}
                  {d.status === 'DRAFT' && (
                    <button
                      className="px-2 py-1 bg-purple-600 text-white text-[10px] font-bold rounded uppercase hover:bg-purple-700"
                      onClick={() => handleTransition(d.id, 'schedule')}
                    >
                      Schedule
                    </button>
                  )}
                  {d.status === 'SCHEDULED' && (
                    <button
                      className="px-2 py-1 bg-emerald-600 text-white text-[10px] font-bold rounded uppercase hover:bg-emerald-700"
                      onClick={() => handleTransition(d.id, 'start')}
                    >
                      Start
                    </button>
                  )}
                  {d.status === 'ACTIVE' && (
                    <button
                      className="px-2 py-1 bg-gray-700 text-white text-[10px] font-bold rounded uppercase hover:bg-gray-900"
                      onClick={() => handleTransition(d.id, 'end')}
                    >
                      End
                    </button>
                  )}
                  {d.status !== 'CANCELLED' && d.status !== 'ENDED' && (
                    <button
                      className="px-2 py-1 bg-red-100 text-red-700 text-[10px] font-bold rounded uppercase hover:bg-red-200"
                      onClick={() => handleTransition(d.id, 'cancel')}
                    >
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
