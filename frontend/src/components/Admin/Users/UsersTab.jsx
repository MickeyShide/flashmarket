import React, { useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { formatDate } from '../../../utils/formatters';
import { usePaginatedResource } from '../../../hooks/usePaginatedResource';
import { InfiniteScrollTrigger } from '../../Common/InfiniteScrollTrigger';
import { AdminTableSkeleton } from '../AdminTableSkeleton';

const PAGE_SIZE = 25;

export const UsersTab = () => {
  const { triggerToast } = useToast();
  const fetchUsersPage = useCallback(({ limit, offset, signal }) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return apiJson(`/admin/users?${params}`, { signal });
  }, []);

  const {
    items: users,
    total,
    loading,
    loadingMore,
    error,
    hasMore,
    reload: loadUsers,
    loadMore
  } = usePaginatedResource({ fetchPage: fetchUsersPage, pageSize: PAGE_SIZE });

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleChangeRole = async (userId, newRole) => {
    if (!window.confirm(`Изменить роль пользователя на ${newRole}?`)) return;
    try {
      await apiJson(`/admin/users/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });

      triggerToast('Роль успешно изменена!');
      loadUsers();
    } catch (err) {
      triggerToast(err.message || 'Ошибка изменения роли', true);
    }
  };

  const handleToggleActive = async (userObj) => {
    const actionText = userObj.is_active ? 'заблокировать' : 'разблокировать';
    if (!window.confirm(`Вы уверены, что хотите ${actionText} этого пользователя?`)) return;

    try {
      await apiJson(`/admin/users/${userObj.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !userObj.is_active })
      });
      triggerToast(`Пользователь ${userObj.email} ${!userObj.is_active ? 'активирован' : 'заблокирован'}`);
      loadUsers();
    } catch (err) {
      triggerToast(err.message || 'Ошибка изменения статуса пользователя', true);
    }
  };

  if (loading) return <AdminTableSkeleton rows={5} />;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-black uppercase">Управление пользователями ({total})</h3>

      {error && users.length === 0 && (
        <button className="text-xs font-bold uppercase text-red-700" onClick={loadUsers}>Повторить загрузку</button>
      )}

      {/* Mobile User Cards List (< md screens) */}
      <div className="md:hidden space-y-3">
        {users.length === 0 ? (
          <div className="bg-white border border-border-color rounded-lg p-6 text-center text-xs text-gray-500">
            Пользователи не найдены
          </div>
        ) : (
          users.map(u => (
            <div key={u.id} className="bg-white border border-border-color rounded-lg p-3.5 space-y-3 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h4 className="font-extrabold text-xs uppercase">{u.full_name || u.email}</h4>
                  <div className="text-[10px] text-gray-400 font-mono">{u.email}</div>
                </div>
                <span className={`text-[8.5px] font-black px-1.5 py-0.5 rounded uppercase shrink-0 ${
                  u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                }`}>
                  {u.is_active ? 'АКТИВЕН' : 'ЗАБЛОКИРОВАН'}
                </span>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-gray-100 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase">Роль:</span>
                  <select
                    className="border p-1 rounded font-mono font-bold text-[10px] uppercase bg-gray-50 cursor-pointer"
                    value={u.role || 'CUSTOMER'}
                    onChange={(e) => handleChangeRole(u.id, e.target.value)}
                  >
                    <option value="CUSTOMER">CUSTOMER</option>
                    <option value="ADMIN">ADMIN</option>
                  </select>
                </div>
                <div className="text-[10px] text-gray-400 font-mono">{formatDate(u.created_at)}</div>
              </div>

              <button
                className={`w-full py-2 text-[11px] font-bold rounded uppercase cursor-pointer ${
                  u.is_active ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                }`}
                onClick={() => handleToggleActive(u)}
              >
                {u.is_active ? 'Заблокировать' : 'Активировать'}
              </button>
            </div>
          ))
        )}
      </div>

      {/* Desktop Users Table (>= md screens) */}
      <div className="hidden md:block bg-white border border-border-color rounded-lg overflow-x-auto w-full">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-[10px] font-black uppercase text-gray-500">
              <th className="p-3">Пользователь</th>
              <th className="p-3">Роль</th>
              <th className="p-3">Статус</th>
              <th className="p-3">Дата регистрации</th>
              <th className="p-3 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs">
            {users.map(u => (
              <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                <td className="p-3 font-extrabold uppercase">
                  <div>{u.full_name || u.email}</div>
                  <div className="text-[10px] text-gray-400 font-mono">{u.email}</div>
                </td>
                <td className="p-3">
                  <select
                    className="border p-1 rounded font-mono font-bold text-[10px] uppercase cursor-pointer"
                    value={u.role || 'CUSTOMER'}
                    onChange={(e) => handleChangeRole(u.id, e.target.value)}
                  >
                    <option value="CUSTOMER">CUSTOMER</option>
                    <option value="ADMIN">ADMIN</option>
                  </select>
                </td>
                <td className="p-3">
                  <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase ${
                    u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {u.is_active ? 'АКТИВЕН' : 'ЗАБЛОКИРОВАН'}
                  </span>
                </td>
                <td className="p-3 font-mono text-[10.5px]">{formatDate(u.created_at)}</td>
                <td className="p-3 text-right">
                  <button
                    className={`px-2.5 py-1 text-[10px] font-bold rounded uppercase cursor-pointer ${
                      u.is_active ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                    }`}
                    onClick={() => handleToggleActive(u)}
                  >
                    {u.is_active ? 'Заблокировать' : 'Активировать'}
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
        error={users.length > 0 ? error : null}
        onLoadMore={loadMore}
      />
    </div>
  );
};
