import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';

const flattenCategoryTree = (nodes, depth = 0) => nodes.flatMap(category => [
  { ...category, depth },
  ...flattenCategoryTree(category.children || [], depth + 1)
]);

export const CategoriesTab = () => {
  const { triggerToast } = useToast();
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [parentId, setParentId] = useState('');
  const [saving, setSaving] = useState(false);

  const loadCategories = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiJson('/api/v1/categories');
      setCategories(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Failed to load categories:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) {
      triggerToast('Укажите название и slug категории', true);
      return;
    }

    setSaving(true);
    try {
      const body = {
        name: name.trim(),
        parent_id: parentId || null
      };
      if (slug.trim()) body.slug = slug.trim();

      await apiJson('/api/v1/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      triggerToast('Категория успешно создана!');
      setName('');
      setSlug('');
      setParentId('');
      loadCategories();
    } catch (err) {
      triggerToast(err.message || 'Ошибка создания категории', true);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="spinner"></div>;

  const flatCategories = flattenCategoryTree(categories);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Category Tree List */}
      <div className="md:col-span-2 bg-white border border-border-color rounded-lg p-5">
        <h3 className="text-sm font-black uppercase mb-4">Дерево категорий ({flatCategories.length})</h3>
        {flatCategories.length === 0 ? (
          <div className="text-xs text-gray-500 py-4">Нет категорий</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {flatCategories.map(cat => (
              <div key={cat.id} className="py-2.5 flex items-center justify-between text-xs">
                <div style={{ paddingLeft: `${cat.depth * 16}px` }}>
                  <div className="font-extrabold uppercase flex items-center gap-2">
                    <span>{cat.name}</span>
                    {cat.depth > 0 && (
                      <span className="text-[9px] font-bold bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                        Дочерняя
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-gray-500 font-mono">slug: {cat.slug} · ID: {cat.id}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Form */}
      <div className="bg-white border border-border-color rounded-lg p-5">
        <h3 className="text-sm font-black uppercase mb-4">Создать категорию</h3>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-bold uppercase mb-1">Название *</label>
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
              required
              className="w-full border p-2 rounded outline-none focus:border-black font-mono text-[11px]"
              placeholder="category-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
          </div>

          <div>
            <label className="block font-bold uppercase mb-1">Родительская категория</label>
            <select
              className="w-full border p-2 rounded outline-none focus:border-black font-sans"
              value={parentId}
              onChange={(e) => setParentId(e.target.value)}
            >
              <option value="">Без родителя (Корневая)</option>
              {flatCategories.map(c => (
                <option key={c.id} value={c.id}>
                  {'— '.repeat(c.depth)}{c.name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full bg-black text-white py-2.5 rounded font-black uppercase tracking-wider hover:bg-gray-800 disabled:opacity-50 mt-2"
          >
            {saving ? 'Создание...' : 'Создать категорию'}
          </button>
        </form>
      </div>
    </div>
  );
};
