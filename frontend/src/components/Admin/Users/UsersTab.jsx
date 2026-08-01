import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { formatDate } from '../../../utils/formatters';

export const UsersTab = () => {
  const { triggerToast } = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiJson('/admin/users?limit=100');
      setUsers(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.warn('Failed to load users list:', err);
    } finally {
      setLoading(false);
    }
  }, []);

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

  if (loading) return <div className="spinner"></div>;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-black uppercase">Управление пользователями ({users.length})</h3>

      <div className="bg-white border border-border-color rounded-lg overflow-hidden">
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
                    className="border p-1 rounded font-mono font-bold text-[10px] uppercase"
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
                    className={`px-2.5 py-1 text-[10px] font-bold rounded uppercase ${
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
    </div>
  );
};
