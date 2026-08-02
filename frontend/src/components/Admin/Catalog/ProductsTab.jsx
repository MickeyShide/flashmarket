import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { formatPrice } from '../../../utils/formatters';
import { useToast } from '../../../context/ToastContext';
import { MediaUploader } from '../../Media/MediaUploader';
import { VariantsTab } from './VariantsTab';
import { StockTab } from '../Inventory/StockTab';

const flattenCategoryTree = (nodes, depth = 0) => nodes.flatMap(category => [
  { ...category, depth },
  ...flattenCategoryTree(category.children || [], depth + 1)
]);

export const ProductsTab = () => {
  const { triggerToast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);

  const [editingProduct, setEditingProduct] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  // Product Form state
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [brandId, setBrandId] = useState('');
  const [status, setStatus] = useState('HIDDEN');
  const [coverImage, setCoverImage] = useState('');
  const [images, setImages] = useState([]);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [activeData, hiddenData, archivedData, catsData, brandsData] = await Promise.all([
        apiJson('/api/v1/products?limit=100&status=ACTIVE'),
        apiJson('/api/v1/products?limit=100&status=HIDDEN'),
        apiJson('/api/v1/products?limit=100&status=ARCHIVED'),
        apiJson('/api/v1/categories').catch(() => []),
        apiJson('/api/v1/brands').catch(() => [])
      ]);
      const productItems = [activeData, hiddenData, archivedData]
        .flatMap(data => Array.isArray(data) ? data : (data.items || []));
      setProducts(productItems);
      setTotal(productItems.length);
      setCategories(Array.isArray(catsData) ? catsData : []);
      setBrands(Array.isArray(brandsData) ? brandsData : []);
    } catch (err) {
      triggerToast('Ошибка загрузки каталога: ' + err.message, true);
    } finally {
      setLoading(false);
    }
  }, [triggerToast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingProduct(null);
    setIsCreating(true);
    setName('');
    setSlug('');
    setDescription('');
    setPrice('');
    setCategoryId('');
    setBrandId('');
    setStatus('HIDDEN');
    setCoverImage('');
    setImages([]);
  };

  const handleOpenEdit = (p) => {
    setEditingProduct(p);
    setIsCreating(false);
    setName(p.name || '');
    setSlug(p.slug || '');
    setDescription(p.description || '');
    setPrice(p.price !== undefined ? String(p.price) : '');
    setCategoryId(p.category_id || '');
    setBrandId(p.brand_id || '');
    setStatus(p.status || 'HIDDEN');
    setCoverImage(p.cover_image || '');
    setImages((p.images || []).map(image => ({ url: image.url, sort_order: image.sort_order || 0 })));
  };

  const handleCloseForm = () => {
    setEditingProduct(null);
    setIsCreating(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !price || !categoryId) {
      triggerToast('Укажите название, цену и категорию', true);
      return;
    }

    setSaving(true);
    try {
      const body = {
        name: name.trim(),
        price: parseFloat(price),
        status,
        description: description.trim(),
        category_id: categoryId,
        brand_id: brandId || null,
        cover_image: coverImage || null,
        images: images.map((image, index) => ({ url: image.url, sort_order: index }))
      };
      if (slug.trim()) body.slug = slug.trim();

      if (editingProduct) {
        // Edit product: PATCH /api/v1/products/{id}
        await apiJson(`/api/v1/products/${editingProduct.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        triggerToast('Товар успешно обновлен!');
      } else {
        // Create product: POST /api/v1/products
        const newProd = await apiJson('/api/v1/products', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        triggerToast('Товар создан! Теперь можно добавить варианты и изображения');
        setEditingProduct(newProd);
        setIsCreating(false);
      }

      loadData();
    } catch (err) {
      triggerToast(err.message || 'Ошибка сохранения товара', true);
    } finally {
      setSaving(false);
    }
  };

  const handleArchiveProduct = async (productId) => {
    if (!window.confirm('Архивировать этот товар?')) return;
    try {
      await apiJson(`/api/v1/products/${productId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'ARCHIVED' })
      });
      triggerToast('Товар архивирован');
      loadData();
    } catch (err) {
      triggerToast(err.message || 'Ошибка архивации товара', true);
    }
  };

  if (loading) return <div className="spinner"></div>;

  const visibleProducts = products.filter(product => {
    const matchesStatus = statusFilter === 'ALL' || product.status === statusFilter;
    const phrase = search.trim().toLowerCase();
    const matchesSearch = !phrase || `${product.name} ${product.slug}`.toLowerCase().includes(phrase);
    return matchesStatus && matchesSearch;
  });
  const flatCategories = flattenCategoryTree(categories);

  return (
    <div className="space-y-6">
      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h3 className="text-sm font-black uppercase">Управление товарами ({total})</h3>
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <input className="border rounded px-2.5 py-1.5 text-xs flex-1 sm:flex-initial" placeholder="Поиск товара..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="border rounded px-2 py-1.5 text-xs font-bold uppercase" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="ALL">Все статусы</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="HIDDEN">HIDDEN</option>
            <option value="ARCHIVED">ARCHIVED</option>
          </select>
          <button
            className="bg-black text-white px-4 py-2 rounded text-xs font-black uppercase tracking-wider hover:bg-gray-800 w-full sm:w-auto mt-1 sm:mt-0 cursor-pointer"
            onClick={handleOpenCreate}
          >
            + Создать товар
          </button>
        </div>
      </div>

      {/* Product Edit / Create Modal or Card */}
      {(isCreating || editingProduct) && (
        <div className="bg-white border-2 border-black rounded-lg p-6 space-y-6">
          <div className="flex items-center justify-between border-b pb-3">
            <h4 className="text-sm font-black uppercase">
              {isCreating ? 'Создание товара (По умолчанию HIDDEN)' : `Редактирование: ${editingProduct.name}`}
            </h4>
            <button className="text-xs font-bold text-gray-500 hover:text-black" onClick={handleCloseForm}>
              ✕ Закрыть
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold uppercase mb-1">Название товара *</label>
                <input
                  type="text"
                  required
                  className="w-full border p-2 rounded outline-none focus:border-black font-sans"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Slug</label>
                <input
                  type="text"
                  className="w-full border p-2 rounded outline-none focus:border-black font-mono text-[11px]"
                  placeholder="автогенерация из названия"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Базовая цена (₽) *</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  className="w-full border p-2 rounded outline-none focus:border-black font-bold"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Статус публикации *</label>
                <select
                  className="w-full border p-2 rounded outline-none focus:border-black font-bold uppercase"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  <option value="HIDDEN">HIDDEN (Скрыт)</option>
                  <option value="ACTIVE">ACTIVE (Опубликован)</option>
                  <option value="ARCHIVED">ARCHIVED (Архив)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Категория</label>
                <select
                  className="w-full border p-2 rounded outline-none focus:border-black"
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                >
                  <option value="">Без категории</option>
                  {flatCategories.map(c => (
                    <option key={c.id} value={c.id}>{'— '.repeat(c.depth)}{c.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold uppercase mb-1">Бренд</label>
                <select
                  className="w-full border p-2 rounded outline-none focus:border-black"
                  value={brandId}
                  onChange={(e) => setBrandId(e.target.value)}
                >
                  <option value="">Без бренда</option>
                  {brands.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">Описание товара</label>
              <textarea
                className="w-full border p-2 rounded outline-none focus:border-black font-sans"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">Обложка товара (Media Upload)</label>
              {editingProduct ? (
                <MediaUploader
                  purpose="product_image"
                  entityType="product"
                  entityId={editingProduct.id}
                  currentUrl={coverImage}
                  onSuccess={(url) => setCoverImage(url)}
                  label="Загрузить обложку"
                />
              ) : <div className="text-[10px] text-gray-500">Сначала создайте товар</div>}
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">Галерея</label>
              <div className="flex gap-2 flex-wrap mb-2">
                {images.map((image, index) => (
                  <div key={`${image.url}-${index}`} className="relative w-16 h-16">
                    <img src={image.url} alt="" className="w-full h-full object-cover rounded" />
                    <button
                      type="button"
                      className="absolute -top-1 -right-1 bg-black text-white rounded-full w-5 h-5 text-[10px]"
                      onClick={() => setImages(current => current.filter((_, itemIndex) => itemIndex !== index))}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              {editingProduct && (
                <MediaUploader
                  purpose="product_image"
                  entityType="product"
                  entityId={editingProduct.id}
                  onSuccess={(url) => setImages(current => [...current, { url, sort_order: current.length }])}
                  label="Добавить изображение"
                />
              )}
            </div>

            <button
              type="submit"
              disabled={saving}
              className="bg-black text-white px-6 py-3 rounded font-black uppercase tracking-wider hover:bg-gray-800 disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : editingProduct ? 'Сохранить изменения' : 'Создать товар'}
            </button>
          </form>

          {/* If Editing existing product: Render Variants & Stock tabs */}
          {editingProduct && (
            <div className="pt-6 border-t border-gray-200 space-y-6">
              <VariantsTab product={editingProduct} onProductUpdated={loadData} />
              <StockTab product={editingProduct} />
            </div>
          )}
        </div>
      )}

      {/* Mobile Product Cards List (< md screens) */}
      <div className="md:hidden space-y-3">
        {visibleProducts.length === 0 ? (
          <div className="bg-white border border-border-color rounded-lg p-6 text-center text-xs text-gray-500">
            Товары не найдены
          </div>
        ) : (
          visibleProducts.map(p => (
            <div key={p.id} className="bg-white border border-border-color rounded-lg p-3.5 flex flex-col justify-between gap-3 shadow-sm">
              <div className="flex items-start gap-3">
                {p.cover_image ? (
                  <img src={p.cover_image} alt="" className="w-14 h-14 object-cover rounded bg-black shrink-0" />
                ) : (
                  <div className="w-14 h-14 bg-black text-white text-[9px] font-bold rounded flex items-center justify-center shrink-0">
                    NO IMG
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-black text-xs uppercase truncate">{p.name}</h4>
                    <span className={`text-[8.5px] font-black px-1.5 py-0.5 rounded uppercase shrink-0 ${
                      p.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' :
                      p.status === 'HIDDEN' ? 'bg-amber-100 text-amber-800' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {p.status}
                    </span>
                  </div>

                  <div className="text-[10px] text-gray-400 font-mono mt-0.5">slug: {p.slug}</div>

                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
                    <div className="font-black text-xs text-black">{formatPrice(p.price, p.currency, false)}</div>
                    <div className="text-[10px] text-gray-500 font-mono">
                      {p.brand_name || '-'} / {p.category_name || '-'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
                <button
                  className="flex-1 py-2 bg-black text-white text-[11px] font-bold rounded uppercase hover:bg-gray-800 cursor-pointer text-center"
                  onClick={() => handleOpenEdit(p)}
                >
                  Редактировать
                </button>
                {p.status !== 'ARCHIVED' && (
                  <button
                    className="px-3 py-2 bg-red-100 text-red-700 text-[11px] font-bold rounded uppercase hover:bg-red-200 cursor-pointer"
                    onClick={() => handleArchiveProduct(p.id)}
                  >
                    В архив
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Desktop Products Table (>= md screens) */}
      <div className="hidden md:block bg-white border border-border-color rounded-lg overflow-x-auto w-full">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-[10px] font-black uppercase text-gray-500">
              <th className="p-3">Товар</th>
              <th className="p-3">Статус</th>
              <th className="p-3">Цена</th>
              <th className="p-3">Бренд / Категория</th>
              <th className="p-3 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs">
            {visibleProducts.map(p => (
              <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                <td className="p-3 font-extrabold uppercase">
                  <div className="flex items-center gap-3">
                    {p.cover_image ? (
                      <img src={p.cover_image} alt="" className="w-9 h-9 object-cover rounded bg-black" />
                    ) : (
                      <div className="w-9 h-9 bg-black text-white text-[9px] font-bold rounded flex items-center justify-center">
                        NO IMG
                      </div>
                    )}
                    <div>
                      <div>{p.name}</div>
                      <div className="text-[10px] text-gray-400 font-mono">slug: {p.slug}</div>
                    </div>
                  </div>
                </td>
                <td className="p-3">
                  <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase ${
                    p.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' :
                    p.status === 'HIDDEN' ? 'bg-amber-100 text-amber-800' : 'bg-gray-200 text-gray-700'
                  }`}>
                    {p.status}
                  </span>
                </td>
                <td className="p-3 font-extrabold">{formatPrice(p.price, p.currency, false)}</td>
                <td className="p-3 text-gray-500 font-mono text-[10.5px]">
                  {p.brand_name || '-'} / {p.category_name || '-'}
                </td>
                <td className="p-3 text-right space-x-2">
                  <button
                    className="px-2.5 py-1 bg-black text-white text-[10px] font-bold rounded uppercase hover:bg-gray-800 cursor-pointer"
                    onClick={() => handleOpenEdit(p)}
                  >
                    Редактировать
                  </button>
                  {p.status !== 'ARCHIVED' && (
                    <button
                      className="px-2 py-1 bg-red-100 text-red-700 text-[10px] font-bold rounded uppercase hover:bg-red-200 cursor-pointer"
                      onClick={() => handleArchiveProduct(p.id)}
                    >
                      В архив
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
