import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { MediaUploader } from '../../Media/MediaUploader';

export const BrandsTab = () => {
  const { triggerToast } = useToast();
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [editingBrand, setEditingBrand] = useState(null);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [logoUrl, setLogoUrl] = useState('');
  const [saving, setSaving] = useState(false);

  const loadBrands = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiJson('/api/v1/brands');
      setBrands(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBrands();
  }, [loadBrands]);

  const handleEdit = (brand) => {
    setEditingBrand(brand);
    setName(brand.name || '');
    setSlug(brand.slug || '');
    setDescription(brand.description || '');
    setLogoUrl(brand.logo_url || '');
  };

  const handleResetForm = () => {
    setEditingBrand(null);
    setName('');
    setSlug('');
    setDescription('');
    setLogoUrl('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || (!editingBrand && !slug.trim())) {
      triggerToast('Для нового бренда укажите название и slug', true);
      return;
    }

    setSaving(true);
    try {
      const body = {
        name: name.trim(),
        description: description.trim(),
        logo_url: logoUrl || null
      };
      if (slug.trim()) body.slug = slug.trim();

      if (editingBrand) {
        // PATCH /api/v1/brands/{brand_id}
        await apiJson(`/api/v1/brands/${editingBrand.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        }).catch(async () => {
          // Fallback PUT
          return await apiJson(`/api/v1/brands/${editingBrand.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          });
        });
        triggerToast('Бренд обновлен!');
      } else {
        // POST /api/v1/brands
        await apiJson('/api/v1/brands', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        triggerToast('Бренд создан!');
      }

      handleResetForm();
      loadBrands();
    } catch (err) {
      triggerToast(err.message || 'Ошибка сохранения бренда', true);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="spinner"></div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Brands Table List */}
      <div className="md:col-span-2 bg-white border border-border-color rounded-lg p-5">
        <h3 className="text-sm font-black uppercase mb-4">Список брендов ({brands.length})</h3>
        {brands.length === 0 ? (
          <div className="text-xs text-gray-500 py-4">Нет созданных брендов</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {brands.map(b => (
              <div key={b.id} className="py-3 flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  {b.logo_url ? (
                    <img src={b.logo_url} alt={b.name} loading="lazy" decoding="async" className="w-8 h-8 object-contain rounded bg-black" />
                  ) : (
                    <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center font-bold font-mono">
                      {b.name.charAt(0)}
                    </div>
                  )}
                  <div>
                    <div className="font-extrabold uppercase">{b.name}</div>
                    <div className="text-[10px] text-gray-500 font-mono">slug: {b.slug}</div>
                  </div>
                </div>

                <button
                  className="px-2.5 py-1 bg-black text-white text-[10px] font-bold rounded uppercase hover:bg-gray-800"
                  onClick={() => handleEdit(b)}
                >
                  Редактировать
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Form */}
      <div className="bg-white border border-border-color rounded-lg p-5">
        <h3 className="text-sm font-black uppercase mb-4">
          {editingBrand ? 'Редактировать бренд' : 'Создать бренд'}
        </h3>

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
              required={!editingBrand}
              className="w-full border p-2 rounded outline-none focus:border-black font-mono text-[11px]"
              placeholder={editingBrand ? 'slug нельзя изменить' : 'brand-slug'}
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
          </div>

          <div>
            <label className="block font-bold uppercase mb-1">Описание</label>
            <textarea
              className="w-full border p-2 rounded outline-none focus:border-black font-sans"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div>
            <label className="block font-bold uppercase mb-1">Логотип бренда</label>
            {editingBrand ? (
              <MediaUploader
                purpose="brand_logo"
                entityType="brand"
                entityId={editingBrand.id}
                currentUrl={logoUrl}
                onSuccess={(url) => setLogoUrl(url)}
                label="Загрузить логотип"
              />
            ) : <div className="text-[10px] text-gray-500">Сначала создайте бренд</div>}
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-black text-white py-2.5 rounded font-black uppercase tracking-wider hover:bg-gray-800 disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : editingBrand ? 'Сохранить' : 'Создать'}
            </button>
            {editingBrand && (
              <button
                type="button"
                className="px-3 bg-gray-200 text-black py-2.5 rounded font-bold uppercase hover:bg-gray-300"
                onClick={handleResetForm}
              >
                Отмена
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};
