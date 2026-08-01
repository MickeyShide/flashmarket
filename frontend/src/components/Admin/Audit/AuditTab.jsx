import React, { useState, useEffect, useCallback } from 'react';
import { apiJson } from '../../../services/api';
import { formatDate } from '../../../utils/formatters';

export const AuditTab = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadAuditLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiJson('/admin/audit-events?limit=100');
      setLogs(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.warn('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAuditLogs();
  }, [loadAuditLogs]);

  if (loading) return <div className="spinner"></div>;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-black uppercase">Журнал аудит-событий ({logs.length})</h3>

      <div className="bg-white border border-border-color rounded-lg overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-[10px] font-black uppercase text-gray-500">
              <th className="p-3">Действие</th>
              <th className="p-3">Пользователь</th>
              <th className="p-3">Детали / Payload</th>
              <th className="p-3">Дата</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs font-mono">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-4 text-center text-gray-400">Нет записанных событий аудита</td>
              </tr>
            ) : (
              logs.map((log, idx) => (
                <tr key={log.id || idx} className="hover:bg-gray-50 transition-colors">
                  <td className="p-3 font-extrabold uppercase text-purple-700">{log.action || log.event_type}</td>
                  <td className="p-3 text-gray-700">{log.actor_user_id || '-'}</td>
                  <td className="p-3 text-[10.5px] text-gray-600 truncate max-w-xs">
                    {JSON.stringify(log.event_data || { subject_user_id: log.subject_user_id })}
                  </td>
                  <td className="p-3 text-[10.5px] text-gray-500">{formatDate(log.created_at || log.timestamp)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
