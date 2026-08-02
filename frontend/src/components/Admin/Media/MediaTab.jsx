import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { formatDate } from '../../../utils/formatters';
import { usePaginatedResource } from '../../../hooks/usePaginatedResource';
import { InfiniteScrollTrigger } from '../../Common/InfiniteScrollTrigger';

const PAGE_SIZE = 25;

export const MediaTab = () => {
  const { triggerToast } = useToast();
  const [purposeFilter, setPurposeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [debouncedPurpose, setDebouncedPurpose] = useState('');

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedPurpose(purposeFilter.trim()), 250);
    return () => window.clearTimeout(timeout);
  }, [purposeFilter]);

  const fetchAssetsPage = useCallback(({ limit, offset, signal }) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (debouncedPurpose) params.set('purpose', debouncedPurpose);
    if (statusFilter) params.set('asset_status', statusFilter);
    return apiJson(`/api/v1/media/admin/assets?${params}`, { signal });
  }, [debouncedPurpose, statusFilter]);

  const {
    items: assets,
    total,
    loading,
    loadingMore,
    error,
    hasMore,
    reload: loadAssets,
    loadMore
  } = usePaginatedResource({ fetchPage: fetchAssetsPage, pageSize: PAGE_SIZE });

  useEffect(() => {
    loadAssets();
  }, [debouncedPurpose, statusFilter, loadAssets]);

  const handleDeleteAsset = async (assetId) => {
    if (!window.confirm('Удалить этот медиа файл?')) return;
    try {
      await apiJson(`/api/v1/media/assets/${assetId}`, { method: 'DELETE' });
      triggerToast('Файл удален');
      loadAssets();
    } catch (err) {
      triggerToast(err.message || 'Ошибка удаления', true);
    }
  };

  if (loading) return <div className="spinner"></div>;

  const visibleAssets = assets;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-black uppercase">Медиа файлы и ассеты ({total})</h3>
      <div className="flex gap-2">
        <input className="border rounded px-2 py-1 text-xs" placeholder="purpose" value={purposeFilter} onChange={(e) => setPurposeFilter(e.target.value)} />
        <select className="border rounded px-2 py-1 text-xs" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Все статусы</option>
          <option value="READY">READY</option>
          <option value="PENDING">PENDING</option>
          <option value="REJECTED">REJECTED</option>
          <option value="DELETED">DELETED</option>
        </select>
      </div>

      {error && assets.length === 0 && (
        <button className="text-xs font-bold uppercase text-red-700" onClick={loadAssets}>Повторить загрузку</button>
      )}

      {/* Mobile Media Cards List (< md screens) */}
      <div className="md:hidden space-y-3">
        {visibleAssets.length === 0 ? (
          <div className="bg-white border border-border-color rounded-lg p-6 text-center text-xs text-gray-500">
            Медиа файлы не найдены
          </div>
        ) : (
          visibleAssets.map(a => (
            <div key={a.id} className="bg-white border border-border-color rounded-lg p-3.5 flex items-center justify-between gap-3 shadow-sm">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                {a.public_url ? (
                  <img src={a.public_url} alt="" loading="lazy" decoding="async" className="w-12 h-12 object-cover rounded bg-black shrink-0" />
                ) : (
                  <div className="w-12 h-12 bg-gray-100 rounded flex items-center justify-center text-[9px] font-mono text-gray-400 shrink-0">
                    NO URL
                  </div>
                )}

                <div className="min-w-0 flex-1">
                  <div className="font-bold text-xs uppercase truncate">{a.original_filename || a.id}</div>
                  <div className="text-[10px] text-gray-400 font-mono">цель: {a.purpose || 'general'}</div>
                  <div className="text-[9.5px] text-gray-500 font-mono mt-0.5">{formatDate(a.created_at)}</div>
                </div>
              </div>

              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className={`text-[8.5px] font-black px-1.5 py-0.5 rounded uppercase ${
                  a.status === 'READY' ? 'bg-emerald-100 text-emerald-800' :
                  a.status === 'PENDING' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                }`}>
                  {a.status}
                </span>

                <button
                  className="px-2.5 py-1 bg-red-100 text-red-700 text-[10px] font-bold rounded uppercase hover:bg-red-200 cursor-pointer"
                  onClick={() => handleDeleteAsset(a.id)}
                >
                  Удалить
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Desktop Media Table (>= md screens) */}
      <div className="hidden md:block bg-white border border-border-color rounded-lg overflow-x-auto w-full">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-[10px] font-black uppercase text-gray-500">
              <th className="p-3">Превью</th>
              <th className="p-3">Файл / Назначение</th>
              <th className="p-3">Сущность</th>
              <th className="p-3">Статус</th>
              <th className="p-3">Дата</th>
              <th className="p-3 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs">
            {visibleAssets.map(a => (
              <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                <td className="p-3">
                  {a.public_url ? (
                    <img src={a.public_url} alt="" loading="lazy" decoding="async" className="w-10 h-10 object-cover rounded bg-black" />
                  ) : (
                    <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center text-[9px] font-mono text-gray-400">
                      NO URL
                    </div>
                  )}
                </td>
                <td className="p-3 font-extrabold">
                  <div>{a.original_filename || a.id}</div>
                  <div className="text-[10px] text-gray-400 font-mono">цель: {a.purpose || 'general'}</div>
                </td>
                <td className="p-3 font-mono text-[10.5px]">
                  {a.entity_type || '-'}: {a.entity_id || '-'}
                </td>
                <td className="p-3">
                  <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase ${
                    a.status === 'READY' ? 'bg-emerald-100 text-emerald-800' :
                    a.status === 'PENDING' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {a.status}
                  </span>
                </td>
                <td className="p-3 font-mono text-[10.5px]">{formatDate(a.created_at)}</td>
                <td className="p-3 text-right">
                  <button
                    className="px-2 py-1 bg-red-100 text-red-700 text-[10px] font-bold rounded uppercase hover:bg-red-200 cursor-pointer"
                    onClick={() => handleDeleteAsset(a.id)}
                  >
                    Удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <InfiniteScrollTrigger
        hasMore={hasMore}
        loading={loadingMore}
        error={assets.length > 0 ? error : null}
        onLoadMore={loadMore}
      />
    </div>
  );
};
